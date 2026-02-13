import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Plus, Trash2 } from 'lucide-react';
import { integrationsAPI } from '../services/api';

export default function IntegrationModal({ isOpen, onClose, userId, onIntegrationsChanged }) {
  const [availableIntegrations, setAvailableIntegrations] = useState([]);
  const [userIntegrations, setUserIntegrations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null); // integrationId to delete

  // Simple in-memory cache for available integrations
  let cachedAvailableIntegrations = null;

  const loadIntegrations = async (force = false) => {
    setLoading(true);
    try {
      let available;
      if (!cachedAvailableIntegrations || force) {
        available = await integrationsAPI.getAvailableIntegrations();
        cachedAvailableIntegrations = available;
      } else {
        available = cachedAvailableIntegrations;
      }
      const user = await integrationsAPI.getUserIntegrations(userId);
      setAvailableIntegrations(available);
      setUserIntegrations(user);
    } catch (error) {
      // Optionally show a toast or error UI
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && userId) {
      loadIntegrations();
    }
  }, [isOpen, userId]);

  const OAUTH_INTEGRATIONS = availableIntegrations
    .filter(i => i.oauth === true || i.authType === 'oauth2')
    .map(i => i.id);

  const handleConnect = async (integrationId) => {
    try {
      const result = await integrationsAPI.connectIntegration(userId, integrationId);
      if (OAUTH_INTEGRATIONS.includes(integrationId) && result.authUrl) {
        window.open(result.authUrl, '_blank');
      } else {
        await loadIntegrations(true); // force reload
        if (onIntegrationsChanged) onIntegrationsChanged();
      }
    } catch (error) {}
  };

  const handleDelete = async (integrationId) => {
    try {
      await integrationsAPI.disconnectIntegration(userId, integrationId);
      setConfirmDelete(null);
      await loadIntegrations(true); // force reload
      if (onIntegrationsChanged) onIntegrationsChanged();
    } catch (error) {}
  };

  const isConnected = (integrationId) => {
    return userIntegrations.some(integration => integration.id === integrationId);
  };

  // Merge available and user integrations for a single list
  const mergedIntegrations = availableIntegrations.map(integration => {
    const connected = userIntegrations.find(i => i.id === integration.id);
    return connected
      ? { ...integration, status: 'connected', connectedAt: connected.connectedAt }
      : { ...integration, status: 'available' };
  });

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">Manage Integrations</h2>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[70vh]">
            {loading ? (
              <div className="text-center py-8">
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
                <p className="text-gray-500 mt-2 text-sm">Loading integrations...</p>
              </div>
            ) : (
              <div className="space-y-3">
                {mergedIntegrations.map(integration => (
                  <div
                    key={integration.id}
                    className={`flex items-center justify-between p-4 border rounded-lg ${
                      integration.status === 'connected'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {typeof integration.icon === 'string' ? (
                          <img src={integration.icon} alt={integration.name} className="w-7 h-7" />
                        ) : (
                          integration.icon
                        )}
                      </span>
                      <div>
                        <p className="font-medium text-gray-900">{integration.name}</p>
                        <p className="text-sm text-gray-600">{integration.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {integration.status === 'connected' && (
                        <span className="text-green-700 bg-green-100 px-2 py-1 rounded text-xs font-semibold mr-2">Connected</span>
                      )}
                      {integration.status === 'connected' ? (
                        <button
                          onClick={() => setConfirmDelete(integration.id)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Remove integration"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleConnect(integration.id)}
                          className="flex items-center gap-2 px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <Plus className="w-4 h-4" />
                          <span className="text-sm font-medium">Connect</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {/* Confirm Delete Dialog */}
          {confirmDelete && (
            <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
              <div className="bg-white rounded-xl shadow-lg p-8 max-w-sm w-full text-center">
                <h3 className="text-lg font-semibold mb-4 text-gray-900">Remove Integration</h3>
                <p className="text-gray-700 mb-6">
                  Are you sure you want to remove this integration? This action cannot be undone.
                </p>
                <div className="flex justify-center gap-4">
                  <button
                    onClick={() => setConfirmDelete(null)}
                    className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleDelete(confirmDelete)}
                    className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
} 