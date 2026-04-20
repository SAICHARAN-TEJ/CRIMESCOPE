<script setup lang="ts">
/**
 * SecureUpload — Direct-to-MinIO upload with pre-signed URLs.
 *
 * Flow:
 *   1. User selects files
 *   2. Login to get JWT
 *   3. Get pre-signed URL from backend
 *   4. Upload file directly to MinIO (never through backend)
 *   5. Notify backend and start analysis
 *   6. Connect WebSocket for real-time updates
 */

import { ref } from "vue";
import axios from "axios";
import { useAnalysisStore } from "@/stores/analysisStore";
import { useWebSocket } from "@/composables/useWebSocket";
import type { PresignedURLResponse, TokenResponse, UploadFile, JobResponse } from "@/types";

const store = useAnalysisStore();
const { connect } = useWebSocket();

const files = ref<File[]>([]);
const isUploading = ref(false);
const uploadProgress = ref(0);
const loginError = ref("");

const username = ref("admin");
const password = ref("crimescope");

const API = "/api/v1";

function onFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files) {
    files.value = Array.from(input.files);
  }
}

function onDrop(event: DragEvent) {
  event.preventDefault();
  if (event.dataTransfer?.files) {
    files.value = Array.from(event.dataTransfer.files);
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault();
}

async function startAnalysis() {
  if (files.value.length === 0) return;
  isUploading.value = true;
  loginError.value = "";

  try {
    // Step 1: Login
    const loginRes = await axios.post<TokenResponse>(`${API}/auth/token`, {
      username: username.value,
      password: password.value,
    });
    const jwt = loginRes.data.access_token;
    store.setToken(jwt);

    const headers = { Authorization: `Bearer ${jwt}` };
    const uploadedFiles: UploadFile[] = [];

    // Step 2: Upload each file via pre-signed URL
    for (let i = 0; i < files.value.length; i++) {
      const file = files.value[i];
      uploadProgress.value = Math.round(((i) / files.value.length) * 100);

      // Get pre-signed URL
      const presignRes = await axios.post<PresignedURLResponse>(
        `${API}/upload/presign`,
        { filename: file.name, content_type: file.type || "application/octet-stream" },
        { headers }
      );

      // Upload direct to MinIO
      await axios.put(presignRes.data.upload_url, file, {
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });

      uploadedFiles.push({
        object_key: presignRes.data.object_key,
        filename: file.name,
        content_type: file.type || "application/octet-stream",
        file_size: file.size,
      });
    }

    uploadProgress.value = 100;

    // Step 3: Start analysis
    const jobRes = await axios.post<JobResponse>(
      `${API}/analysis/start`,
      { files: uploadedFiles },
      { headers }
    );

    store.startJob(jobRes.data.job_id);

    // Step 4: Connect WebSocket for real-time updates
    connect(jobRes.data.job_id);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "Upload failed";
    loginError.value = msg;
    store.setError(msg);
  } finally {
    isUploading.value = false;
  }
}
</script>

<template>
  <div class="upload">
    <h2 class="upload__title">📁 Upload Evidence</h2>
    <p class="upload__desc">
      Drop files here or click to select. Files upload directly to secure storage — never through the API.
    </p>

    <!-- Credentials (demo) -->
    <div class="upload__creds">
      <div class="upload__field">
        <label>Username</label>
        <input v-model="username" type="text" placeholder="admin" />
      </div>
      <div class="upload__field">
        <label>Password</label>
        <input v-model="password" type="password" placeholder="password" />
      </div>
    </div>

    <!-- Drop Zone -->
    <div
      class="upload__dropzone"
      @drop="onDrop"
      @dragover="onDragOver"
    >
      <input
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.mp4,.avi,.mov,.jpg,.png"
        class="upload__input"
        @change="onFileSelect"
      />
      <div class="upload__icon">⬆️</div>
      <p v-if="files.length === 0">Drag & drop files or click to browse</p>
      <div v-else class="upload__files">
        <div v-for="f in files" :key="f.name" class="upload__file">
          <span class="upload__filename">{{ f.name }}</span>
          <span class="upload__filesize">{{ (f.size / 1024).toFixed(0) }} KB</span>
        </div>
      </div>
    </div>

    <!-- Progress -->
    <div v-if="isUploading" class="upload__progress">
      <div class="upload__progress-bar">
        <div class="upload__progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
      <span class="upload__progress-text">{{ uploadProgress }}%</span>
    </div>

    <!-- Error -->
    <p v-if="loginError" class="upload__error">{{ loginError }}</p>

    <!-- Start Button -->
    <button
      class="upload__btn"
      :disabled="files.length === 0 || isUploading"
      @click="startAnalysis"
    >
      {{ isUploading ? "Uploading..." : "🚀 Start Analysis" }}
    </button>
  </div>
</template>

<style scoped>
.upload__title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 6px;
}

.upload__desc {
  font-size: 13px;
  color: var(--cs-text-muted);
  margin-bottom: 16px;
}

.upload__creds {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.upload__field {
  flex: 1;
}

.upload__field label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--cs-text-muted);
  margin-bottom: 4px;
}

.upload__field input {
  width: 100%;
  padding: 8px 12px;
  background: var(--cs-bg);
  border: 1px solid var(--cs-border);
  border-radius: 8px;
  color: var(--cs-text);
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
  outline: none;
  transition: border-color var(--cs-transition);
}

.upload__field input:focus {
  border-color: var(--cs-primary);
}

.upload__dropzone {
  position: relative;
  border: 2px dashed var(--cs-border);
  border-radius: var(--cs-radius);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: border-color var(--cs-transition), background var(--cs-transition);
}

.upload__dropzone:hover {
  border-color: var(--cs-primary);
  background: rgba(59, 130, 246, 0.05);
}

.upload__input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.upload__icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.upload__files {
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
}

.upload__file {
  display: flex;
  justify-content: space-between;
  padding: 6px 12px;
  background: var(--cs-bg);
  border-radius: 6px;
  font-size: 13px;
}

.upload__filename {
  font-weight: 500;
}

.upload__filesize {
  color: var(--cs-text-muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
}

.upload__progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.upload__progress-bar {
  flex: 1;
  height: 6px;
  background: var(--cs-bg);
  border-radius: 3px;
  overflow: hidden;
}

.upload__progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cs-primary), var(--cs-accent));
  border-radius: 3px;
  transition: width 0.3s ease;
}

.upload__progress-text {
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  color: var(--cs-text-muted);
  min-width: 40px;
}

.upload__error {
  color: var(--cs-danger);
  font-size: 13px;
  margin: 8px 0;
}

.upload__btn {
  width: 100%;
  padding: 12px;
  margin-top: 12px;
  background: linear-gradient(135deg, var(--cs-primary), #2563eb);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--cs-transition), transform var(--cs-transition);
}

.upload__btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.upload__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
