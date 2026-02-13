import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading'); // 'loading', 'success', 'error'
  const [message, setMessage] = useState('');
  const [queryString, setQueryString] = useState('');

  useEffect(() => {
    setQueryString(window.location.search);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('success') === 'jira') {
      setStatus('success');
      setMessage('Jira connected!');
      setTimeout(() => {
        if (window.opener) {
          window.opener.location.reload();
          window.close();
        } else {
          window.location.href = '/chat';
        }
      }, 1500);
    } else if (params.get('success') === 'slack') {
      setStatus('success');
      setMessage('Slack connected!');
      setTimeout(() => {
        if (window.opener) {
          window.opener.location.reload();
          window.close();
        } else {
          window.location.href = '/chat';
        }
      }, 1500);
    } else if (params.get('error')) {
      setStatus('error');
      setMessage('Connection Failed: ' + params.get('error'));
    } else {
      setStatus('error');
      setMessage('Connection Failed: Invalid callback parameters.');
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      {/* Show the query string for debugging */}
      <div style={{ marginBottom: 16, color: '#888', fontSize: 14 }}>
        Query: {queryString}
      </div>
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <div className="flex items-center justify-center mb-4">
              <span className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <span className="w-4 h-4 bg-blue-500 rounded-full animate-pulse"></span>
              </span>
            </div>
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Connecting...</h2>
            <p className="text-gray-600">Please wait while we complete the connection.</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="flex items-center justify-center mb-4">
              <span className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
                <span className="w-4 h-4 bg-green-500 rounded-full"></span>
              </span>
            </div>
            <h2 className="text-lg font-semibold text-green-700 mb-2">{message}</h2>
            <p className="text-gray-600">You can close this window.</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="flex items-center justify-center mb-4">
              <span className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
                <span className="w-4 h-4 bg-red-500 rounded-full"></span>
              </span>
            </div>
            <h2 className="text-lg font-semibold text-red-700 mb-2">Error</h2>
            <p className="text-gray-600">{message}</p>
            <button
              onClick={() => window.location.href = '/chat'}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Go to Chat
            </button>
          </>
        )}
      </div>
    </div>
  );
} 