import React, { useState } from 'react';
import { motion } from 'framer-motion';
import CustomSignIn from '../components/CustomSignIn';
import CustomSignUp from '../components/CustomSignUp';

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);

  const handleAuthSuccess = (data) => {
    // Redirect to chat page after successful auth
    window.location.href = '/chat';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo/Brand */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl mx-auto mb-4 flex items-center justify-center max-md:w-12 max-md:h-12">
            <span className="text-white text-2xl font-bold max-md:text-xl">U</span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2 max-md:text-2xl">Welcome to Uni</h1>
          <p className="text-gray-600 max-md:text-sm">Your unified AI assistant</p>
        </div>

        {/* Auth Container */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100 max-md:p-6">
          {/* Toggle between Login and Signup */}
          <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all max-md:py-1.5 max-md:px-2 max-md:text-xs ${
                isLogin
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all max-md:py-1.5 max-md:px-2 max-md:text-xs ${
                !isLogin
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Sign Up
            </button>
          </div>

          {/* Custom Auth Forms */}
          {isLogin ? (
            <CustomSignIn
              onSuccess={handleAuthSuccess}
              onSwitchToSignUp={() => setIsLogin(false)}
            />
          ) : (
            <CustomSignUp
              onSuccess={handleAuthSuccess}
              onSwitchToLogin={() => setIsLogin(true)}
            />
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-gray-500 max-md:text-xs">
          <p>By continuing, you agree to our Terms of Service and Privacy Policy</p>
        </div>
      </motion.div>
    </div>
  );
} 