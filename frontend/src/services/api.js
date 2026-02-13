import { supabase } from '../lib/supabaseClient';

const API_BASE_URL = 'http://localhost:8000';

// Chat History API
export const chatAPI = {
  // Get chat history for a user (all sessions if sessionId is not provided)
  getHistory: async (userId, sessionId) => {
    const params = new URLSearchParams({ user_id: userId });
    if (sessionId) params.append('session_id', sessionId);
    const response = await fetch(`${API_BASE_URL}/chat/history?${params}`);
    if (!response.ok) throw new Error('Failed to fetch chat history');
    return response.json();
  },

  // Save a chat message (session_id is required)
  saveMessage: async (userId, message, sender, sessionId) => {
    if (!sessionId) throw new Error('session_id is required');
    const response = await fetch(`${API_BASE_URL}/chat/history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        message,
        sender,
        session_id: sessionId,
      }),
    });
    if (!response.ok) throw new Error('Failed to save message');
    return response.json();
  },

  // Send a prompt to the AI
  sendPrompt: async (prompt, userId) => {
    const response = await fetch(`${API_BASE_URL}/prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        user_id: userId,
      }),
    });
    if (!response.ok) throw new Error('Failed to send prompt');
    return response.json();
  },
};

// Integrations API (mock for now - replace with actual endpoints)
export const integrationsAPI = {
  // Get user's connected integrations
  getUserIntegrations: async (userId) => {
    console.log('Getting integrations for user:', userId); // Debug log
    // Query both notion_integration and slack_integration tables for this user
    const [{ data: notion, error: notionError }, { data: slack, error: slackError }, { data: jira, error: jiraError }] = await Promise.all([
      supabase.from('notion_integration').select('*').eq('user_id', userId),
      supabase.from('slack_integration').select('*').eq('user_id', userId),
      supabase.from('jira_integration').select('*').eq('user_id', userId),
    ]);
    
    console.log('Notion data:', notion, 'Notion error:', notionError); // Debug log
    console.log('Slack data:', slack, 'Slack error:', slackError); // Debug log
    console.log('Jira data:', jira, 'Jira error:', jiraError); // Debug log
    
    const integrations = [];
    if (notion && notion.length > 0) {
      integrations.push({
        id: 'notion',
        name: 'Notion',
        status: 'connected',
        icon: '/logos/notion_logo.png', // Use correct image filename
        description: 'Notes, docs, and knowledge base',
        connectedAt: notion[0].created_at,
      });
    }
    if (slack && slack.length > 0) {
      integrations.push({
        id: 'slack',
        name: 'Slack',
        status: 'connected',
        icon: '/logos/slack_logo.png', // Use correct image filename
        description: 'Team communication and channels',
        connectedAt: slack[0].created_at,
      });
    }
    if (jira && jira.length > 0) {
      integrations.push({
        id: 'jira',
        name: 'Jira',
        status: 'connected',
        icon: '/logos/jira_logo.png', // Use correct image filename
        description: 'Project management and issue tracking',
        connectedAt: jira[0].created_at,
      });
    }
    
    console.log('Final integrations array:', integrations); // Debug log
    return integrations;
  },

  // Connect a new integration
  connectIntegration: async (userId, integrationId) => {
    if (integrationId === 'slack') {
      // Get Slack OAuth URL from backend
      const response = await fetch(`${API_BASE_URL}/oauth/authorize?user_id=${userId}`);
      if (!response.ok) throw new Error('Failed to get Slack OAuth URL');
      const data = await response.json();
      return { success: true, authUrl: data.auth_url };
    }
    if (integrationId === 'jira') {
      // Get Jira OAuth URL from backend
      const response = await fetch(`${API_BASE_URL}/jira/oauth/authorize?user_id=${userId}`);
      if (!response.ok) throw new Error('Failed to get Jira OAuth URL');
      const data = await response.json();
      return { success: true, authUrl: data.auth_url };
    }
    // For other integrations, use mock implementation
    console.log(`Connecting ${integrationId} for user ${userId}`);
    return { success: true, integrationId };
  },

  // Disconnect an integration
  disconnectIntegration: async (userId, integrationId) => {
    if (integrationId === 'slack') {
      // Delete from slack_integration table
      const { error } = await supabase
        .from('slack_integration')
        .delete()
        .eq('user_id', userId);
      
      if (error) throw new Error('Failed to disconnect Slack integration');
      return { success: true, integrationId };
    }
    if (integrationId === 'jira') {
      // Delete from jira_integration table
      const { error } = await supabase
        .from('jira_integration')
        .delete()
        .eq('user_id', userId);
      if (error) throw new Error('Failed to disconnect Jira integration');
      return { success: true, integrationId };
    }
    // Mock implementation - replace with actual API call
    console.log(`Disconnecting ${integrationId} for user ${userId}`);
    return { success: true, integrationId };
  },

  // Get available integrations
  getAvailableIntegrations: async () => {
    // Mock data - replace with actual API call
    return [
      {
        id: 'slack',
        name: 'Slack',
        description: 'Team communication and channels',
        icon: '/logos/slack_logo.png', // Use correct image filename
        color: 'bg-purple-100',
        status: 'available',
        oauth: true, // Mark as OAuth
      },
      {
        id: 'notion',
        name: 'Notion',
        description: 'Notes, docs, and knowledge base',
        icon: '/logos/notion_logo.png', // Use correct image filename
        color: 'bg-gray-100',
        status: 'available',
      },
      {
        id: 'jira',
        name: 'Jira',
        description: 'Project management and issue tracking',
        icon: '/logos/jira_logo.png', // Use correct image filename
        color: 'bg-blue-100',
        status: 'available',
        oauth: true, // Mark as OAuth
      },
    ];
  },

  // Test function to debug Supabase queries
  testSupabaseQuery: async (userId) => {
    console.log('=== TESTING SUPABASE QUERY ===');
    console.log('User ID:', userId);
    
    try {
      const result = await supabase.from('slack_integration').select('*').eq('user_id', userId);
      console.log('Raw Supabase result:', result);
      console.log('Data:', result.data);
      console.log('Error:', result.error);
      console.log('Count:', result.data?.length);
      return result;
    } catch (error) {
      console.error('Supabase query error:', error);
      return { error };
    }
  },
}; 