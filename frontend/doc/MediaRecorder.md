我使用 MediaRecorder API 和 RecordRTC 解决了这个问题。我设置了每隔 20 秒自动开始录制。由于它使用之前打开的流，因此无需用户反复授予录制权限。这解决了 .webm 文件头的问题。

步骤 1：获取屏幕流

要录制屏幕，我们使用 navigator.mediaDevices.getDisplayMedia()。此函数会提示用户授予屏幕访问权限，并返回一个 MediaStream，我们可以将其传递给录制器。

JavaScript
let screenStream = null;
async function getScreenStream() {
if (!screenStream) {
  screenStream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: true,
});
console.log("Screen stream initialized.");
}
return screenStream;
}
步骤二：分段开始屏幕录制

startScreenRecording 函数使用 RecordRTCPromisesHandler 初始化一个 20 秒的录制会话。20 秒录制结束后，录制的数据块会被发送到服务器，并立即开始一个新的录制会话。

JavaScript
let isRecording = false;
async function startScreenRecording() {
console.log("Starting screen recording...");
let recordedChunks = [];

try {
if (isRecording) return;
isRecording = true;

const stream = await getScreenStream();
const recorder = new RecordRTCPromisesHandler(stream, {
  type: "video",
  mimeType: "video/webm",
  timeSlice: 20000,  // 20-second chunks
});

await recorder.startRecording();

setTimeout(async () => {
  await recorder.stopRecording();
  isRecording = false;

  const blob = await recorder.getBlob();
  console.log("Recording stopped, sending file...");

  if (!blob || !(blob instanceof Blob)) {
    console.error("Error: Invalid Blob received.");
    return;
  }
  await sendChunksToServer(blob);
  startScreenRecording();
}, 20000);  // 20 seconds
} catch (err) {
console.error("Error accessing media devices:", err);
}
}
步骤 3：向服务器发送数据块

JavaScript
async function sendChunksToServer(blob) {
try {
const formData = new FormData();
formData.append("video_chunk", blob, "chunk.webm");

const response = await fetch("https://yourserver.com/upload", {
  method: "POST",
  body: formData,
});

if (!response.ok) throw new Error("Failed to upload chunk");
console.log("Chunk uploaded successfully.");
} catch (error) {
console.error("Error uploading chunk:", error);
}
}
📌 要点总结

屏幕录制通过getDisplayMedia()启动。
使用 RecordRTC 记录数据块，时间切片为：20000（20 秒）。
每个录制的数据块都以 .webm 文件的形式发送到服务器。
每次上传后都会自动开始新的录制会话，以保持录制过程的连续性。