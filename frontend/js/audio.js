// frontend/js/audio.js
// Audio utilities with better recording and format handling

class AudioRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.startTime = null;
    this.onResult = null;
    this.onError = null;
    this.stream = null;
    this.recordingTimeout = null;
    this.maxRecordingTime = 30000; // 30 detik max
  }

  async startRecording(onResult, onError) {
    this.onResult = onResult;
    this.onError = onError;

    try {
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 44100,
          channelCount: 1,
        },
      });

      // Check supported MIME types (prioritaskan yang paling kompatibel)
      let mimeType = null;
      const supportedTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
      ];

      for (const type of supportedTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          mimeType = type;
          break;
        }
      }

      if (!mimeType) {
        mimeType = "audio/webm"; // fallback
      }

      console.log(`Using MIME type: ${mimeType}`);

      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000,
      });

      this.audioChunks = [];
      this.isRecording = true;
      this.startTime = Date.now();

      // Handle data
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
          console.log(`Chunk received: ${event.data.size} bytes`);
        }
      };

      // Handle stop
      this.mediaRecorder.onstop = async () => {
        console.log("Recording stopped, processing audio...");
        await this.processAudio();
        this.cleanup();
      };

      // Handle error
      this.mediaRecorder.onerror = (event) => {
        console.error("MediaRecorder error:", event);
        if (this.onError) {
          this.onError("Recording error occurred. Please try again.");
        }
        this.cleanup();
      };

      // Start recording
      this.mediaRecorder.start(1000); // Record in 1-second chunks

      // Set max recording time (auto-stop after 30 seconds)
      if (this.recordingTimeout) {
        clearTimeout(this.recordingTimeout);
      }
      this.recordingTimeout = setTimeout(() => {
        if (this.isRecording) {
          console.log("Max recording time reached, auto-stopping...");
          this.stopRecording();
          if (this.onError) {
            this.onError("Recording timeout. Please try again.");
          }
        }
      }, this.maxRecordingTime);

      console.log("Recording started successfully");
    } catch (error) {
      console.error("Error starting recording:", error);
      if (
        error.name === "NotAllowedError" ||
        error.name === "PermissionDeniedError"
      ) {
        if (this.onError) {
          this.onError(
            "Microphone access denied. Please allow microphone access and try again.",
          );
        }
      } else {
        if (this.onError) {
          this.onError("Could not access microphone: " + error.message);
        }
      }
      this.cleanup();
    }
  }

  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      console.log("Stopping recording...");
      this.isRecording = false;
      this.mediaRecorder.stop();
    } else {
      console.log("No active recording to stop");
    }
  }

  async processAudio() {
    const duration = Date.now() - this.startTime;
    console.log(
      `Recording duration: ${duration}ms, chunks: ${this.audioChunks.length}`,
    );

    // Validate recording
    if (duration < 1000) {
      if (this.onError) {
        this.onError("Please speak for at least 1 second.");
      }
      return;
    }

    if (this.audioChunks.length === 0) {
      if (this.onError) {
        this.onError("No audio data captured. Please try again.");
      }
      return;
    }

    // Create blob from chunks
    let audioBlob;
    try {
      audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
      console.log(`Audio blob created: ${audioBlob.size} bytes`);

      if (audioBlob.size < 1000) {
        if (this.onError) {
          this.onError(
            "Audio too short or quiet. Please speak louder and try again.",
          );
        }
        return;
      }
    } catch (error) {
      console.error("Error creating blob:", error);
      if (this.onError) {
        this.onError("Error processing audio. Please try again.");
      }
      return;
    }

    // Send to backend
    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      console.log("Sending audio to backend...");

      const response = await fetch("/api/stt", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("Backend response:", data);

      if (!response.ok) {
        if (data.error) {
          throw new Error(data.error);
        } else {
          throw new Error(`Server error: ${response.status}`);
        }
      }

      if (data.text && data.text.trim().length > 0) {
        if (this.onResult) {
          this.onResult(data.text.trim());
        }
      } else {
        if (this.onError) {
          this.onError(
            "No speech detected. Please speak clearly and try again.",
          );
        }
      }
    } catch (error) {
      console.error("Error sending audio:", error);
      if (this.onError) {
        this.onError(
          error.message || "Network error. Please check your connection.",
        );
      }
    }
  }

  cleanup() {
    // Stop all tracks
    if (this.stream) {
      this.stream.getTracks().forEach((track) => {
        track.stop();
        console.log("Track stopped");
      });
      this.stream = null;
    }

    // Clear timeout
    if (this.recordingTimeout) {
      clearTimeout(this.recordingTimeout);
      this.recordingTimeout = null;
    }

    // Reset state
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;

    console.log("Cleanup completed");
  }

  // Check if currently recording
  isCurrentlyRecording() {
    return this.isRecording;
  }
}

// ============================================
// GLOBAL INSTANCE
// ============================================

const audioRecorder = new AudioRecorder();

// ============================================
// MAIN RECORDING FUNCTION
// ============================================

function startRecording() {
  // Get DOM elements
  const voiceBtn = document.getElementById("voiceBtn");
  const messageInput = document.getElementById("messageInput");
  const showToastFn =
    window.showToast ||
    function (msg, type) {
      console.log(`Toast [${type}]: ${msg}`);
    };

  // If currently recording, stop it
  if (audioRecorder.isCurrentlyRecording()) {
    console.log("Stopping recording...");
    audioRecorder.stopRecording();

    // Update UI
    if (voiceBtn) {
      voiceBtn.classList.remove("listening");
      voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
      voiceBtn.title = "Click to speak";
    }
    if (messageInput) {
      messageInput.placeholder = "Type your message in English...";
      messageInput.disabled = false;
    }
    showToastFn("Processing your speech...", "info");
    return;
  }

  // Start recording
  console.log("Starting recording...");

  // Update UI
  if (voiceBtn) {
    voiceBtn.classList.add("listening");
    voiceBtn.innerHTML = '<i class="fas fa-stop"></i>';
    voiceBtn.title = "Click to stop recording";
  }
  if (messageInput) {
    messageInput.placeholder = "🎤 Recording... Click mic to stop";
    messageInput.disabled = true;
  }
  showToastFn("Recording... Speak clearly!", "info");

  // Start recording with callbacks
  audioRecorder.startRecording(
    // On success - text recognized
    (text) => {
      console.log("✅ Speech recognized:", text);

      // Update UI
      if (voiceBtn) {
        voiceBtn.classList.remove("listening");
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.title = "Click to speak";
      }
      if (messageInput) {
        messageInput.placeholder = "Type your message in English...";
        messageInput.disabled = false;
      }

      // Show result
      showToastFn("✅ Speech recognized!", "success");

      // Set input and send
      if (messageInput && text) {
        messageInput.value = text;
        // Auto-send after a short delay
        setTimeout(() => {
          if (typeof sendMessage === "function") {
            sendMessage(text);
          }
        }, 500);
      }
    },
    // On error
    (error) => {
      console.error("❌ Recording error:", error);

      // Update UI
      if (voiceBtn) {
        voiceBtn.classList.remove("listening");
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.title = "Click to speak";
      }
      if (messageInput) {
        messageInput.placeholder = "Type your message in English...";
        messageInput.disabled = false;
      }

      // Show error
      showToastFn(
        error || "Could not understand audio. Please try again.",
        "error",
      );
    },
  );
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener("DOMContentLoaded", () => {
  console.log("Audio.js initialized");

  // Override voice button
  const voiceBtn = document.getElementById("voiceBtn");
  if (voiceBtn) {
    // Remove any existing listeners
    const newVoiceBtn = voiceBtn.cloneNode(true);
    voiceBtn.parentNode.replaceChild(newVoiceBtn, voiceBtn);

    // Add click listener
    newVoiceBtn.addEventListener("click", startRecording);

    console.log("Voice button configured");
  } else {
    console.warn("Voice button not found");
  }

  // Handle page unload - cleanup
  window.addEventListener("beforeunload", () => {
    if (audioRecorder.isCurrentlyRecording()) {
      audioRecorder.stopRecording();
    }
  });
});

// ============================================
// EXPOSE FUNCTIONS GLOBALLY
// ============================================

window.startRecording = startRecording;
window.audioRecorder = audioRecorder;

console.log("Audio.js loaded successfully");
