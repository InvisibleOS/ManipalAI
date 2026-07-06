import { NextRequest, NextResponse } from 'next/server';
import { groq } from '@ai-sdk/groq';
import { streamText } from 'ai';
import { supabase } from '@/utils/db';
import { embedWithBackoff } from '@/utils/embeddings';

export async function POST(request: NextRequest) {
  try {
    const { messages } = await request.json();

    if (!messages || messages.length === 0) {
      return NextResponse.json({ error: 'Messages are required' }, { status: 400 });
    }

    // Get the latest user query
    const latestUserMessage = messages[messages.length - 1];
    if (latestUserMessage.role !== 'user') {
      return NextResponse.json({ error: 'Latest message must be from user' }, { status: 400 });
    }

    const query = latestUserMessage.content;

    // Step 1: Generate a 768-dimensional embedding of the query
    const queryEmbedding = await embedWithBackoff(query);

    // Step 2: Execute pgvector similarity searches in SQL (ORDER BY + LIMIT via RPC)
    let announcements: { title: string; content: string; similarity: number }[] = [];
    let documents: { title: string; content: string; similarity: number }[] = [];

    const [annResult, docResult] = await Promise.all([
      supabase.rpc('match_announcements', {
        query_embedding: queryEmbedding,
        match_threshold: 0.4,
        match_count: 3,
      }),
      supabase.rpc('match_document_embeddings', {
        query_embedding: queryEmbedding,
        match_threshold: 0.5,
        match_count: 5,
      }),
    ]);

    if (!annResult.error && annResult.data) {
      announcements = annResult.data as { title: string; content: string; similarity: number }[];
    }

    if (!docResult.error && docResult.data) {
      documents = docResult.data as { title: string; content: string; similarity: number }[];
    }

    // Step 3: Append retrieved contexts to system prompt
    let contextStr = '';
    
    if (announcements.length > 0) {
      contextStr += '### RELEVANT ANNOUNCEMENTS:\n';
      announcements.forEach((ann, index) => {
        contextStr += `[Announcement #${index + 1}] Title: ${ann.title}\nContent: ${ann.content} (Similarity: ${(ann.similarity * 100).toFixed(1)}%)\n\n`;
      });
    }

    if (documents.length > 0) {
      contextStr += '### RELEVANT DOCUMENTS & KNOWLEDGE BASE:\n';
      documents.forEach((doc, index) => {
        contextStr += `[Document Chunk #${index + 1}] Source: ${doc.title}\nContent: ${doc.content} (Similarity: ${(doc.similarity * 100).toFixed(1)}%)\n\n`;
      });
    }

    const systemPrompt = `You are a helpful and intelligent virtual assistant for MIT Bengaluru (Campus AI).
Use the following context to answer the user query as accurately as possible. 
If the query cannot be answered using the context, provide a polite response using your general knowledge but note the source.
Ensure you formats response well using markdown structure where appropriate.

${contextStr ? `--- \nRetrieved Context:\n${contextStr}---` : 'No direct context matches found in the knowledge base.'}`;

    // Step 4: Stream response using Groq (Llama 3.3 70b) via Vercel AI SDK
    const result = await streamText({
      model: groq('llama-3.3-70b-versatile'),
      system: systemPrompt,
      messages: messages.map((m: any) => ({
        role: m.role,
        content: m.content,
      })),
    });

    return result.toUIMessageStreamResponse();


  } catch (error: any) {
    console.error('Chat API Error:', error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}
