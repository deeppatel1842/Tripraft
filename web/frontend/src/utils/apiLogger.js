/**
 * API Logger - Frontend
 * Professional logging for API calls with clear visibility
 */

class APILogger {
  constructor() {
    this.enabled = true;
    this.logLevel = 'INFO'; // DEBUG, INFO, WARN, ERROR
  }

  formatTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      fractionalSecondDigits: 3 
    });
  }

  logRequest(method, url, data = null) {
    if (!this.enabled) return;
    
    console.group(`%c→ API REQUEST [${this.formatTimestamp()}]`, 'color: #3b82f6; font-weight: bold;');
    console.log(`%c${method}`, 'color: #10b981; font-weight: bold;', url);
    if (data) {
      console.log('%cPayload:', 'color: #6366f1;', data);
    }
    console.groupEnd();
  }

  logResponse(method, url, status, data, duration) {
    if (!this.enabled) return;
    
    const statusColor = status >= 200 && status < 300 ? '#10b981' : '#ef4444';
    const durationMs = duration.toFixed(2);
    
    console.group(`%c← API RESPONSE [${this.formatTimestamp()}] ${durationMs}ms`, `color: ${statusColor}; font-weight: bold;`);
    console.log(`%c${method}`, 'color: #10b981; font-weight: bold;', url);
    console.log(`%cStatus: ${status}`, `color: ${statusColor}; font-weight: bold;`);
    console.log('%cData:', 'color: #6366f1;', data);
    console.groupEnd();
  }

  logError(method, url, error, duration) {
    if (!this.enabled) return;
    
    const durationMs = duration ? duration.toFixed(2) : 'N/A';
    
    console.group(`%c✗ API ERROR [${this.formatTimestamp()}] ${durationMs}ms`, 'color: #ef4444; font-weight: bold; font-size: 14px;');
    console.log(`%c${method}`, 'color: #ef4444; font-weight: bold;', url);
    console.error('%cError:', 'color: #ef4444; font-weight: bold;', error);
    
    if (error.response) {
      console.log('%cResponse Status:', 'color: #f59e0b;', error.response.status);
      console.log('%cResponse Data:', 'color: #f59e0b;', error.response.data);
    } else if (error.request) {
      console.error('%cNo response received', 'color: #ef4444;');
      console.log('%cRequest:', 'color: #f59e0b;', error.request);
    } else {
      console.error('%cRequest setup error:', 'color: #ef4444;', error.message);
    }
    
    console.groupEnd();
  }

  logInfo(message, data = null) {
    if (!this.enabled) return;
    
    console.log(`%c[INFO] ${message}`, 'color: #3b82f6;', data || '');
  }

  logWarning(message, data = null) {
    if (!this.enabled) return;
    
    console.warn(`%c[WARN] ${message}`, 'color: #f59e0b; font-weight: bold;', data || '');
  }

  logSuccess(message, data = null) {
    if (!this.enabled) return;
    
    console.log(`%c✓ ${message}`, 'color: #10b981; font-weight: bold; font-size: 14px;', data || '');
  }

  separator() {
    if (!this.enabled) return;
    console.log('%c' + '─'.repeat(80), 'color: #64748b;');
  }

  enable() {
    this.enabled = true;
    console.log('%c[API Logger] Enabled', 'color: #10b981; font-weight: bold;');
  }

  disable() {
    this.enabled = false;
    console.log('%c[API Logger] Disabled', 'color: #ef4444; font-weight: bold;');
  }
}

export default new APILogger();
