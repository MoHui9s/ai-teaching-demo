const THROTTLE_MS = 60;

export class SSEClient {
  constructor() {
    this.abortController = null;
    this.accumulatedText = '';
    this.renderThrottleTimer = null;
    this.onChunk = null;
    this.onDone = null;
    this.onError = null;
    this.onStatus = null;
  }

  async streamChat(messages, userId) {
    this.abortController = new AbortController();
    this.accumulatedText = '';

    try {
      const response = await fetch('/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          model: 'hermes',
          stream: true,
          messages,
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') {
              if (this.onDone) this.onDone(this.accumulatedText);
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.choices?.[0]?.delta?.content) {
                this.accumulatedText += parsed.choices[0].delta.content;

                if (this.renderThrottleTimer) {
                  clearTimeout(this.renderThrottleTimer);
                }

                this.renderThrottleTimer = setTimeout(() => {
                  if (this.onChunk) {
                    this.onChunk(this.accumulatedText);
                  }
                }, THROTTLE_MS);
              }

              if (parsed.choices?.[0]?.finish_reason === 'tool_calls') {
                if (this.onStatus) {
                  this.onStatus('Saving memory...');
                }
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e, data);
            }
          }
        }
      }

      if (this.onDone) {
        this.onDone(this.accumulatedText);
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Stream aborted');
        if (this.onDone && this.accumulatedText) {
          this.onDone(this.accumulatedText);
        }
      } else {
        if (this.onError) {
          this.onError(error.message);
        }
      }
    } finally {
      this.abortController = null;
      if (this.renderThrottleTimer) {
        clearTimeout(this.renderThrottleTimer);
        this.renderThrottleTimer = null;
      }
    }
  }

  stop() {
    if (this.abortController) {
      this.abortController.abort();
    }
  }

  isStreaming() {
    return this.abortController !== null;
  }
}