// Purpose: Provides api Logger logic and exports for apps\web\src\utils.
/**
 * API Logger - Frontend
 * No-op implementation for production. All logging functions are silent.
 */

class APILogger {
  constructor() {
    this.enabled = false;
  }

  formatTimestamp() { return ''; }
  logRequest() {}
  logResponse() {}
  logError() {}
  logInfo() {}
  logWarning() {}
  logSuccess() {}
  separator() {}
  enable() { this.enabled = true; }
  disable() { this.enabled = false; }
}

export default new APILogger();
