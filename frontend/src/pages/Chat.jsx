import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, User, Settings, Plus, MessageSquare, LogOut, ChevronLeft, MoreVertical, Edit, Trash } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import { useNavigate } from 'react-router-dom';
import { chatAPI, integrationsAPI } from '../services/api';
import IntegrationModal from '../components/IntegrationModal';
import { v4 as uuidv4 } from 'uuid';
import ReactMarkdown from 'react-markdown';

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [showIntegrations, setShowIntegrations] = useState(false);
  const [integrations, setIntegrations] = useState([]);
  const [showProfile, setShowProfile] = useState(false);
  const [showIntegrationModal, setShowIntegrationModal] = useState(false);
  const [inputAtBottom, setInputAtBottom] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const [showChatMenu, setShowChatMenu] = useState(null); // session_id of open menu
  const [renamingChat, setRenamingChat] = useState(null); // session_id being renamed
  const [newChatName, setNewChatName] = useState('');
  // Replace Rename Modal and always-visible More button with hover logic and inline editing
  const [editingChat, setEditingChat] = useState(null); // session_id being edited
  const [editChatName, setEditChatName] = useState('');
  // Track which chat bar is currently hovered
  const [hoveredChat, setHoveredChat] = useState(null);
  // Track if a new search is being started (for centering input)
  const [startingNewSearch, setStartingNewSearch] = useState(false);
  // Add state for custom delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [pendingDeleteSession, setPendingDeleteSession] = useState(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Get current user
  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      console.log('Current user:', user); // Debug log
      setUser(user);
      if (user) {
        console.log('User ID for integrations:', user.id); // Debug log
        loadChatHistory(user.id);
        loadIntegrations(user.id);
      }
    };
    getUser();
  }, []);

  // Load chat history
  const loadChatHistory = async (userId) => {
    try {
      // Fetch all chat history for the user (all sessions)
      const data = await chatAPI.getHistory(userId);
      setChatHistory(data);
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  // Load user integrations
  const loadIntegrations = async (userId) => {
    try {
      const data = await integrationsAPI.getUserIntegrations(userId);
      console.log('Loaded integrations:', data); // Debug log
      setIntegrations(data);
    } catch (error) {
      console.error('Error loading integrations:', error);
    }
  };

  // Remove integration with confirmation
  const handleRemoveIntegration = async (integrationId) => {
    if (!user?.id) return;
    
    const integration = integrations.find(i => i.id === integrationId);
    const confirmed = window.confirm(
      `Are you sure you want to remove the ${integration?.name} integration? This will disconnect your account and remove all associated data.`
    );
    
    if (confirmed) {
      try {
        await integrationsAPI.disconnectIntegration(user.id, integrationId);
        await loadIntegrations(user.id); // Reload the list
        console.log(`Removed integration: ${integrationId}`); // Debug log
      } catch (error) {
        console.error('Error removing integration:', error);
        alert('Failed to remove integration. Please try again.');
      }
    }
  };

  // Reload integrations when window gains focus (user returns from OAuth)
  useEffect(() => {
    const handleFocus = () => {
      if (user?.id) {
        loadIntegrations(user.id);
      }
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [user?.id]);

  // Send message
  const sendMessage = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;
    // If no chat is selected, create a new session first
    if (!selectedChat) {
      if (!user?.id) return;
      const sessionId = uuidv4();
      // Save the first user message
      const { error } = await supabase.from('chat_history').insert({
        user_id: user.id,
        session_id: sessionId,
        chat_name: '',
        message: trimmedInput,
        sender: 'user',
      });
      if (!error) {
        setSelectedChat({ session_id: sessionId, chat_name: '', message: trimmedInput });
        setStartingNewSearch(false);
        setInput('');
        setIsLoading(true);
        // Immediately update sidebar after user message
        await loadChatHistory(user.id);
        try {
          const data = await chatAPI.sendPrompt(trimmedInput, user?.id || 'default');
          let botContent;
          if ((data.notion_matches && data.notion_matches.length > 0) || (data.slack_matches && data.slack_matches.length > 0)) {
            botContent = JSON.stringify(data);
          } else {
            botContent = data.message || 'Sorry, I encountered an error.';
          }
          const botMessage = {
            id: Date.now() + 1,
            content: botContent,
            sender: 'bot',
            timestamp: new Date().toISOString(),
          };
          setMessages([{ id: Date.now(), content: trimmedInput, sender: 'user', timestamp: new Date().toISOString() }, botMessage]);
          // Save bot message to DB
          await chatAPI.saveMessage(user.id, botMessage.content, 'bot', sessionId);
          // Optionally reload chat history again if you want sidebar to update with bot preview
          // await loadChatHistory(user.id);
        } catch (error) {
          console.error('Error sending message:', error);
          const errorMessage = {
            id: Date.now() + 1,
            content: 'Sorry, I encountered an error. Please try again.',
            sender: 'bot',
            timestamp: new Date().toISOString(),
          };
          setMessages(prev => [...prev, errorMessage]);
        } finally {
          setIsLoading(false);
        }
        return;
      } else {
        alert('Failed to create new search.');
        return;
      }
    }
    if (!inputAtBottom) setInputAtBottom(true);

    const newMessage = {
      id: Date.now(),
      content: trimmedInput,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setIsLoading(true);
    // Immediately update sidebar after user message
    await chatAPI.saveMessage(user.id, trimmedInput, 'user', selectedChat?.session_id);
    await loadChatHistory(user.id);

    try {
      const data = await chatAPI.sendPrompt(trimmedInput, user?.id || 'default');
      let botContent;
      if ((data.notion_matches && data.notion_matches.length > 0) || (data.slack_matches && data.slack_matches.length > 0)) {
        botContent = JSON.stringify(data);
      } else {
        botContent = data.message || 'Sorry, I couldn’t find any information in Slack or Notion.';
      }
      const botMessage = {
        id: Date.now() + 1,
        content: botContent,
        sender: 'bot',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, botMessage]);
      if (user?.id) {
        await chatAPI.saveMessage(user.id, botMessage.content, 'bot', selectedChat?.session_id);
        // Optionally reload chat history again if you want sidebar to update with bot preview
        // await loadChatHistory(user.id);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        content: 'Sorry, I encountered an error. Please try again.',
        sender: 'bot',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter/Shift+Enter for textarea
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Sign out
  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/');
  };

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Group chat history by session_id and get latest message per session
  const groupedChats = Object.values(
    chatHistory.reduce((acc, row) => {
      if (!row.session_id) return acc;
      // Use the latest message per session for preview
      if (!acc[row.session_id] || new Date(row.created_at) > new Date(acc[row.session_id].created_at)) {
        acc[row.session_id] = row;
      }
      return acc;
    }, {})
  ).filter(chat => chat.session_id)
 .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

  // Create a new search/chat session
  const handleNewSearch = async () => {
    setSelectedChat(null);
    setMessages([]);
    setInput('');
    setInputAtBottom(false);
    setStartingNewSearch(true);
  };

  // Rename a chat
  const handleRenameChat = async (sessionId, newName) => {
    if (!user?.id || !newName.trim()) return;
    const { error } = await supabase.from('chat_history')
      .update({ chat_name: newName })
      .eq('user_id', user.id)
      .eq('session_id', sessionId);
    if (!error) {
      await loadChatHistory(user.id);
    } else {
      alert('Failed to rename search.');
    }
  };

  // Delete a chat
  const handleDeleteChat = async (sessionId) => {
    if (!user?.id) return;
    // Remove window.confirm, only use custom dialog
    const { error } = await supabase.from('chat_history')
      .delete()
      .eq('user_id', user.id)
      .eq('session_id', sessionId);
    if (!error) {
      await loadChatHistory(user.id);
      if (selectedChat?.session_id === sessionId) setSelectedChat(null);
    } else {
      alert('Failed to delete search.');
    }
  };

  // Load messages for a selected chat session
  const loadMessagesForSession = async (sessionId) => {
    if (!user?.id || !sessionId) return;
    try {
      const data = await chatAPI.getHistory(user.id, sessionId);
      // Convert to message format expected by the UI
      const formatted = data.map(row => ({
        id: row.id || row.created_at,
        content: row.message,
        sender: row.sender,
        timestamp: row.created_at,
      }));
      setMessages(formatted);
    } catch (error) {
      setMessages([]);
      console.error('Error loading messages for session:', error);
    }
  };

  // When a chat is selected, load its messages
  useEffect(() => {
    if (selectedChat && selectedChat.session_id) {
      loadMessagesForSession(selectedChat.session_id);
    }
  }, [selectedChat]);

  // Responsive layout classes
  const sidebarClass = 'w-80 bg-white border-r border-gray-200 flex flex-col max-md:w-20 max-md:min-w-0 max-md:p-0';
  const mainClass = 'flex-1 flex flex-col min-w-0';

  // Inline rename handler
  const startEditingChat = (sessionId, currentName) => {
    setEditingChat(sessionId);
    setEditChatName(currentName || '');
  };
  const handleEditChatNameChange = (e) => setEditChatName(e.target.value);
  const handleEditChatNameBlur = async (sessionId) => {
    if (editChatName.trim() && editChatName !== groupedChats.find(c => c.session_id === sessionId)?.chat_name) {
      await handleRenameChat(sessionId, editChatName);
    }
    setEditingChat(null);
    setEditChatName('');
  };
  const handleEditChatNameKeyDown = async (e, sessionId) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      await handleEditChatNameBlur(sessionId);
    } else if (e.key === 'Escape') {
      setEditingChat(null);
      setEditChatName('');
    }
  };

  // Compute preview text for a chat session
  const getChatPreview = (sessionId) => {
    // Find the first user message in this session
    const firstUserMsg = chatHistory.find(
      row => row.session_id === sessionId && row.sender === 'user' && row.message && row.message.trim() !== ''
    );
    return firstUserMsg ? firstUserMsg.message.substring(0, 30) + (firstUserMsg.message.length > 30 ? '...' : '') : 'New Search';
  };

  // Add this helper above the Chat component
  function renderStructuredSummary(content) {
    let data;
    try {
      data = typeof content === 'string' ? JSON.parse(content) : content;
    } catch {
      return null;
    }
    if (!data || (!data.notion_matches && !data.slack_matches)) return null;
    return (
      <div style={{ whiteSpace: 'pre-line', fontSize: '0.95rem', color: '#111827' }}>
        {data.notion_matches && data.notion_matches.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Notion Results</div>
            {data.notion_matches.map((item, idx) => (
              <div key={item.permalink} style={{ marginBottom: 12 }}>
                <div>
                  {idx + 1}. <a href={item.permalink} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>{item.title}</a>
                </div>
                <div style={{ marginLeft: 18 }}>
                  Summary: {item.summary}<br />
                  - Last Edited: {item.last_edited}<br />
                  - Status: {item.status}
                </div>
              </div>
            ))}
          </div>
        )}
        {data.slack_matches && data.slack_matches.length > 0 && (
          <div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>Slack Results:</div>
            {data.slack_matches.map((item, idx) => (
              <div key={item.slack_permalink || idx} style={{ marginLeft: 8, marginBottom: 10 }}>
                • Message: "{item.text}"<br />
                • User: {item.user}<br />
                • Location: {item.channel_type}<br />
                • View in Slack: <a href={item.slack_permalink} target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb', textDecoration: 'underline' }}>Link</a>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex max-md:flex-col">
      {/* Sidebar */}
      <div className={sidebarClass}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex items-center gap-3 max-md:justify-center max-md:p-2">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">U</span>
          </div>
          <h1 className="text-lg font-semibold text-gray-900 max-md:hidden">Uni</h1>
          <button
            onClick={handleNewSearch}
            className="ml-auto flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            title="New Search"
          >
            <Plus className="w-4 h-4" />
            <span className="max-md:hidden">New Search</span>
          </button>
        </div>
        {/* Chat/Search Sessions */}
        <div className="flex-1 overflow-y-auto p-4 max-md:hidden">
          <div className="space-y-2">
            {groupedChats.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p className="text-sm">No searches yet</p>
              </div>
            ) : (
              groupedChats.map((chat) => (
                <div
                  key={chat.session_id}
                  className="relative group"
                  onMouseEnter={() => setHoveredChat(chat.session_id)}
                  onMouseLeave={() => { if (showChatMenu === chat.session_id) setShowChatMenu(null); setHoveredChat(null); }}
                >
                  <button
                    onClick={() => setSelectedChat(chat)}
                    className={`w-full text-left p-3 rounded-lg hover:bg-gray-100 transition-colors flex items-center gap-3 ${selectedChat?.session_id === chat.session_id ? 'bg-blue-50' : ''}`}
                  >
                    <MessageSquare className="w-4 h-4 text-gray-400" />
                    <div className="flex-1 min-w-0">
                      {editingChat === chat.session_id ? (
                        <input
                          type="text"
                          value={editChatName}
                          onChange={handleEditChatNameChange}
                          onBlur={() => handleEditChatNameBlur(chat.session_id)}
                          onKeyDown={e => handleEditChatNameKeyDown(e, chat.session_id)}
                          className="w-full border px-2 py-1 rounded text-sm"
                          autoFocus
                        />
                      ) : (
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {chat.chat_name && chat.chat_name.trim() !== '' ? chat.chat_name : getChatPreview(chat.session_id)}
                        </p>
                      )}
                      <p className="text-xs text-gray-500">
                        {new Date(chat.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    {/* Three-dot menu only on hover */}
                    <div className={`ml-2 transition-opacity ${hoveredChat === chat.session_id ? 'opacity-100' : 'opacity-0'}`}>
                      <button
                        onClick={e => { e.stopPropagation(); setShowChatMenu(showChatMenu === chat.session_id ? null : chat.session_id); }}
                        className="p-1 rounded hover:bg-gray-200"
                        title="More options"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  </button>
                  {/* Dropdown menu: only show if this chat is hovered AND showChatMenu matches */}
                  {hoveredChat === chat.session_id && showChatMenu === chat.session_id && (
                    <div className="absolute right-0 top-10 z-20 bg-white border rounded shadow-lg w-40">
                      <button
                        onClick={() => { startEditingChat(chat.session_id, chat.chat_name); setShowChatMenu(null); }}
                        className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100"
                      >
                        <Edit className="w-4 h-4" /> Rename
                      </button>
                      <button
                        onClick={() => { setPendingDeleteSession(chat.session_id); setShowDeleteConfirm(true); setShowChatMenu(null); }}
                        className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                      >
                        <Trash className="w-4 h-4" /> Delete
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      {/* Main Chat Area */}
      <div className={mainClass}>
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between max-md:px-2 max-md:py-2">
          <h2 className="text-lg font-semibold text-gray-900 max-md:text-base">Chat</h2>
          <div className="flex items-center gap-3">
            {/* Integrations Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowIntegrations(!showIntegrations)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors max-md:px-2 max-md:py-1"
              >
                <Settings className="w-4 h-4" />
                <span className="max-md:hidden">Integrations</span>
                <ChevronLeft className={`w-4 h-4 transition-transform ${showIntegrations ? 'rotate-90' : ''}`} />
              </button>
              <AnimatePresence>
                {showIntegrations && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-10 max-md:w-64"
                  >
                    <div className="p-4">
                      <h3 className="text-sm font-semibold text-gray-900 mb-3">Connected Integrations</h3>
                      <div className="space-y-2">
                        {integrations.map((integration) => (
                          <div key={integration.id} className="flex items-center justify-between p-2 rounded-lg bg-gray-50">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">
                                {typeof integration.icon === 'string' ? (
                                  <img src={integration.icon} alt={integration.name} className="w-6 h-6" />
                                ) : (
                                  integration.icon
                                )}
                              </span>
                              <span className="text-sm font-medium">{integration.name}</span>
                            </div>
                            <div className={`w-2 h-2 rounded-full ${integration.status === 'connected' ? 'bg-green-500' : 'bg-gray-400'}`} />
                          </div>
                        ))}
                        <button 
                          onClick={() => {
                            setShowIntegrations(false);
                            setShowIntegrationModal(true);
                          }}
                          className="w-full flex items-center gap-2 p-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Plus className="w-4 h-4" />
                          Manage integrations
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            {/* Profile Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowProfile(!showProfile)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors max-md:px-2 max-md:py-1"
              >
                <User className="w-4 h-4" />
                <span className="max-md:hidden">{user?.user_metadata?.username || user?.email?.split('@')[0] || 'User'}</span>
              </button>
              <AnimatePresence>
                {showProfile && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-10"
                  >
                    <div className="p-2">
                      <button 
                        onClick={() => {
                          setShowProfile(false);
                          navigate('/profile');
                        }}
                        className="w-full flex items-center gap-2 p-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                      >
                        <User className="w-4 h-4" />
                        Profile Settings
                      </button>
                      <button
                        onClick={handleSignOut}
                        className="w-full flex items-center gap-2 p-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Logout
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 max-md:p-2">
          {messages.length === 0 && (startingNewSearch || !selectedChat) ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center w-full max-w-lg mx-auto">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                  <span className="text-white text-2xl font-bold">U</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Welcome to Uni</h3>
                <p className="text-gray-600 mb-6">Your AI assistant is ready to help you</p>
                {/* Centered input until first message is sent */}
                <div className="max-w-md mx-auto">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything..."
                    rows={2}
                    className="w-full px-4 py-3 text-lg border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    style={{ minHeight: 48, maxHeight: 120 }}
                  />
                  <div className="flex justify-end mt-2">
                    <button
                      onClick={sendMessage}
                      disabled={!input.trim() || isLoading}
                      className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
                      message.sender === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-900'
                    }`}
                  >
                    {message.sender === 'bot' ? (
                      <div style={{ fontSize: '0.875rem', whiteSpace: 'pre-line', color: '#111827' }}>
                        {(() => {
                          // Try to render as structured summary if possible
                          const structured = renderStructuredSummary(message.content);
                          if (structured) return structured;
                          // Fallback to markdown
                          return <ReactMarkdown>{message.content}</ReactMarkdown>;
                        })()}
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-line">{message.content}</p>
                    )}
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="bg-gray-200 text-gray-900 px-4 py-3 rounded-2xl">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
        {/* Input Area (jumps to bottom after first message) */}
        {(selectedChat || messages.length > 0) && !startingNewSearch && (
          <div className="p-6 border-t border-gray-200 max-md:p-2 flex justify-center">
            <div className="w-full flex justify-center">
              <div className="flex items-center gap-3 w-full" style={{ maxWidth: '60%' }}>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your message..."
                  rows={2}
                  className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-base max-md:text-sm shadow-sm"
                  style={{ minHeight: 48, maxHeight: 120 }}
                  disabled={isLoading}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || isLoading}
                  className="p-3 bg-blue-600 text-white rounded-2xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Integration Modal */}
        <IntegrationModal
          isOpen={showIntegrationModal}
          onClose={() => setShowIntegrationModal(false)}
          userId={user?.id}
          onIntegrationsChanged={() => user?.id && loadIntegrations(user.id)}
        />
        {/* Custom Delete Confirmation Dialog */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
            <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full">
              <h3 className="text-lg font-semibold mb-2">Delete Search</h3>
              <p className="mb-4 text-gray-700">Are you sure you want to delete this search? This cannot be undone.</p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => { setShowDeleteConfirm(false); setPendingDeleteSession(null); }}
                  className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    await handleDeleteChat(pendingDeleteSession);
                    setShowDeleteConfirm(false);
                    setPendingDeleteSession(null);
                  }}
                  className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 