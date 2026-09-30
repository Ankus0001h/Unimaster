/**
 * streaming.js — Terminal Typing Effect & Realtime Row Streaming FX
 * National Unified Material Master Platform
 */

const StreamingTerminal = (() => {
    'use strict';

    let _terminalEl = null;
    let _bodyEl = null;
    let _queue = [];
    let _isProcessing = false;

    /**
     * Initialize the terminal with DOM references.
     */
    function init(terminalId) {
        _terminalEl = document.getElementById(terminalId);
        if (!_terminalEl) return;
        _bodyEl = _terminalEl.querySelector('.terminal-body');
    }

    /**
     * Show the terminal window.
     */
    function show() {
        if (_terminalEl) {
            _terminalEl.classList.add('visible');
        }
    }

    /**
     * Hide the terminal window.
     */
    function hide() {
        if (_terminalEl) {
            _terminalEl.classList.remove('visible');
        }
    }

    /**
     * Clear all terminal lines.
     */
    function clear() {
        if (_bodyEl) {
            _bodyEl.innerHTML = '';
        }
        _queue = [];
    }

    /**
     * Colorize log tags in a terminal line.
     */
    function _colorize(text) {
        return text
            .replace(/\[PROCESSING\]/g, '<span class="log-tag tag-processing">[PROCESSING]</span>')
            .replace(/\[AI MAPPER\]/g, '<span class="log-tag tag-ai">[AI MAPPER]</span>')
            .replace(/\[SCHEMA\]/g, '<span class="log-tag tag-schema">[SCHEMA]</span>')
            .replace(/\[COMPLETE\]/g, '<span class="log-tag tag-complete">[COMPLETE]</span>')
            .replace(/\[ERROR\]/g, '<span class="log-tag tag-error">[ERROR]</span>')
            .replace(/\[INFO\]/g, '<span class="log-tag tag-processing">[INFO]</span>')
            .replace(/\[MATCH\]/g, '<span class="log-tag tag-ai">[MATCH]</span>')
            .replace(/\[CLUSTER\]/g, '<span class="log-tag tag-schema">[CLUSTER]</span>')
            .replace(/CONFIDENCE:\s*(\d+%?)/gi, 'CONFIDENCE: <span class="confidence">$1</span>');
    }

    /**
     * Write a single line with typing animation delay.
     */
    function writeLine(text, delay) {
        return new Promise((resolve) => {
            setTimeout(() => {
                if (!_bodyEl) { resolve(); return; }
                const line = document.createElement('div');
                line.className = 'terminal-line';
                line.innerHTML = _colorize(text);
                _bodyEl.appendChild(line);
                _bodyEl.scrollTop = _bodyEl.scrollHeight;
                resolve();
            }, delay || 100);
        });
    }

    /**
     * Stream an array of log lines with staggered delays for typing effect.
     */
    async function streamLogs(logs, baseDelay) {
        if (!_bodyEl) return;
        const delay = baseDelay || 120;

        show();

        for (let i = 0; i < logs.length; i++) {
            await writeLine(logs[i], delay + Math.random() * 60);
        }

        // Add blinking cursor at the end
        const cursor = document.createElement('span');
        cursor.className = 'terminal-cursor';
        _bodyEl.appendChild(cursor);
        _bodyEl.scrollTop = _bodyEl.scrollHeight;
    }

    /**
     * Stream table rows into a data table body with delay.
     */
    async function streamTableRows(tableBodyId, rows, renderFn, delay) {
        const tbody = document.getElementById(tableBodyId);
        if (!tbody) return;

        const rowDelay = delay || 80;

        for (let i = 0; i < rows.length; i++) {
            await new Promise((resolve) => {
                setTimeout(() => {
                    const tr = renderFn(rows[i], i);
                    if (tr) {
                        tr.style.opacity = '0';
                        tr.style.transform = 'translateY(8px)';
                        tbody.appendChild(tr);
                        // Trigger animation
                        requestAnimationFrame(() => {
                            tr.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                            tr.style.opacity = '1';
                            tr.style.transform = 'translateY(0)';
                        });
                    }
                    resolve();
                }, rowDelay);
            });
        }
    }

    /**
     * Write a progress-style line that updates in place.
     */
    function writeProgress(text) {
        if (!_bodyEl) return null;
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = _colorize(text);
        _bodyEl.appendChild(line);
        _bodyEl.scrollTop = _bodyEl.scrollHeight;
        return line;
    }

    function updateProgress(lineEl, text) {
        if (lineEl) {
            lineEl.innerHTML = _colorize(text);
        }
    }

    return {
        init,
        show,
        hide,
        clear,
        writeLine,
        streamLogs,
        streamTableRows,
        writeProgress,
        updateProgress,
    };
})();
