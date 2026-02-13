import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Mail, Key, ArrowLeft, Edit2, Save, X } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
import { useNavigate } from 'react-router-dom';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editUsername, setEditUsername] = useState(false);
  const [editPassword, setEditPassword] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      setUser(user);
      setUsername(user?.user_metadata?.username || '');
      setLoading(false);
    };
    getUser();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    navigate('/');
  };

  const handleSaveUsername = async () => {
    setSaving(true);
    const { error } = await supabase.auth.updateUser({ data: { username } });
    setSaving(false);
    if (!error) setEditUsername(false);
  };

  const handleSavePassword = async () => {
    setSaving(true);
    const { error } = await supabase.auth.updateUser({ password });
    setSaving(false);
    if (!error) setEditPassword(false);
    setPassword('');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center">
            <span className="text-white text-2xl font-bold">U</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" />
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="max-w-2xl mx-auto p-6 max-md:p-4">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="max-md:text-sm">Back to Chat</span>
          </button>
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center max-md:w-16 max-md:h-16">
              <User className="w-8 h-8 text-white max-md:w-6 max-md:h-6" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2 max-md:text-xl">Profile Settings</h1>
            <p className="text-gray-600 max-md:text-sm">Manage your account and preferences</p>
          </div>
        </motion.div>
        {/* Profile Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100 max-md:p-6"
        >
          <div className="space-y-6">
            {/* Username */}
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg max-md:p-3">
              <User className="w-5 h-5 text-gray-500 max-md:w-4 max-md:h-4" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 max-md:text-xs">Username</p>
                {editUsername ? (
                  <div className="flex gap-2 mt-1 max-md:flex-col">
                    <input
                      type="text"
                      value={username}
                      onChange={e => setUsername(e.target.value)}
                      className="input-primary max-md:text-sm"
                      disabled={saving}
                    />
                    <div className="flex gap-2 max-md:justify-end">
                      <button onClick={handleSaveUsername} className="btn-primary max-md:px-3 max-md:py-1" disabled={saving}>
                        <Save className="w-4 h-4 max-md:w-3 max-md:h-3" />
                      </button>
                      <button onClick={() => setEditUsername(false)} className="btn-secondary max-md:px-3 max-md:py-1" disabled={saving}>
                        <X className="w-4 h-4 max-md:w-3 max-md:h-3" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-gray-700 max-md:text-sm">{username || 'No username set'}</span>
                    <button onClick={() => setEditUsername(true)} className="btn-secondary max-md:px-2 max-md:py-1">
                      <Edit2 className="w-4 h-4 max-md:w-3 max-md:h-3" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            {/* Email (not editable) */}
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg max-md:p-3">
              <Mail className="w-5 h-5 text-gray-500 max-md:w-4 max-md:h-4" />
              <div>
                <p className="text-sm font-medium text-gray-900 max-md:text-xs">Email</p>
                <p className="text-sm text-gray-600 max-md:text-xs">{user?.email}</p>
              </div>
            </div>
            {/* Password */}
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg max-md:p-3">
              <Key className="w-5 h-5 text-gray-500 max-md:w-4 max-md:h-4" />
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 max-md:text-xs">Password</p>
                {editPassword ? (
                  <div className="flex gap-2 mt-1 max-md:flex-col">
                    <input
                      type="password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      className="input-primary max-md:text-sm"
                      disabled={saving}
                    />
                    <div className="flex gap-2 max-md:justify-end">
                      <button onClick={handleSavePassword} className="btn-primary max-md:px-3 max-md:py-1" disabled={saving || !password}>
                        <Save className="w-4 h-4 max-md:w-3 max-md:h-3" />
                      </button>
                      <button onClick={() => setEditPassword(false)} className="btn-secondary max-md:px-3 max-md:py-1" disabled={saving}>
                        <X className="w-4 h-4 max-md:w-3 max-md:h-3" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-gray-700 max-md:text-sm">••••••••</span>
                    <button onClick={() => setEditPassword(true)} className="btn-secondary max-md:px-2 max-md:py-1">
                      <Edit2 className="w-4 h-4 max-md:w-3 max-md:h-3" />
                    </button>
                  </div>
                )}
              </div>
            </div>
            {/* Actions */}
            <div className="space-y-3 pt-6 border-t border-gray-200">
              <button
                onClick={() => navigate('/chat')}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors font-medium max-md:py-2"
              >
                Back to Chat
              </button>
              <button
                onClick={handleSignOut}
                className="w-full bg-red-600 text-white py-3 px-4 rounded-lg hover:bg-red-700 transition-colors font-medium max-md:py-2"
              >
                Sign Out
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
} 