# 前端 - 摄像头监控系统

这是摄像头监控系统的前端组件。它提供了一个基于 Web 的界面，用于实时视频监控和系统控制。

## 架构

前端结构如下：

- `index.html`: 主页面布局和结构
- `style.css`: 样式和布局定义
- `js/`: JavaScript 库和自定义代码
  - `crypto-js.js`: 加密库
  - `jquery.min.js`: jQuery 库
  - `template-web.js`: 模板渲染
  - `bootstrap-3.4.1-dist/`: Bootstrap 框架
  - `zTree/`: 树视图组件
- `jssdk/`: 摄像头集成的 JavaScript SDK
  - `mcs8Client.js`: 主客户端库
  - `sdkDemo.js`: SDK 演示
  - `videoStreamHandler.js`: 视频流处理
- `img/`: 图像资源
- `video/`: 视频资源 (如果有的话)

## 功能特性

- 实时视频显示从多个摄像头
- 用于监控的交互式界面
- 视频播放控制
- 系统状态可视化
- 响应式设计，适用于不同屏幕尺寸

## Index.html 代码结构分析

index.html 文件是前端的主要入口，包含以下主要部分：

### 1. 头部区域
- 页面元数据定义（字符集、视口、兼容性等）
- CSS 样式表引用（Bootstrap、zTree、自定义样式）
- JavaScript 库引用（jQuery、模板引擎、加密库等）
- 第三方库引用（RecordRTC 用于处理视频块）

### 2. 导航栏
- 应用标题"MCS8 JavaScript Client SDK开发指南"
- 下载链接（教程、WebAPI文档等）

### 3. 主体内容区域
- 左侧菜单：包含快速上手、连接网关、实时视频/对讲、GPS/设备参数、消息上报等功能导航
- 中间内容区域：动态显示各功能模块的界面
- 右侧日志面板：显示操作日志

### 4. 功能模块
- 连接网关：处理与调度台的连接
- 获取设备列表：获取在线/全部设备列表
- 实时视频/音频：开启和关闭视频音频流
- 双向通话：视频和语音通话功能
- GPS 信息：获取实时GPS信息
- 消息上报：GPS、设备状态、报警等消息
- 指令下发：录像指令、工单消息、文本消息等
- 视频流处理：实时视频处理和分析
- 视频文件测试：处理本地视频文件
- 实时视频检测：实时视频检测功能

### 5. 模板定义
- 使用 template-web.js 定义多个功能模块的模板（实时视频、双向通话、设备参数等）

### 6. 底部脚本引用
- 引用 MCS8 JavaScript Client SDK
- 引用 SDK 演示脚本
- 引用视频流处理脚本
- 主要的业务逻辑脚本

## JSSDK 二方包使用说明

前端使用 MCS8 JavaScript Client SDK 进行摄像头和视频流的管理，具体使用方法如下：

### 1. 引入 SDK
在 HTML 文件中引用 SDK 相关脚本。

### 2. 初始化和连接
创建 SDK 实例并配置连接参数，包括用户账号信息、本地视频音频元素、网关连接参数等，然后连接到网关服务器。

### 3. 主要功能使用示例
- 连接网关：处理与调度台的连接
- 获取设备列表：获取在线/全部设备列表
- 实时视频处理：开启和关闭视频流
- 实时音频处理：开启和关闭音频流
- 双向视频通话：创建视频通话组

### 4. 消息回调处理
SDK 通过 `onReceived` 方法处理各种回调消息，包括：
- `ConnecteInfo`: 连接成功
- `responseConnectGateway`: 连接响应
- `JoinRoomAndProduct`: 创建群组
- `joinRoom`: 加入房间
- `gpsUpload`: GPS 上传
- `DeviceStatus`: 设备状态
- `AlarmUpload`: 报警上传
- 等等

## 视频帧传递给后端的机制

在 index.html 中，视频帧通过以下几种方式传递给后端：

### 1. 实时视频流处理
使用 RecordRTC 库进行录制，将视频流按时间分块（每60秒一个块），每个块都有完整的头部信息。定时停止录制、发送数据块并重新开始录制。

### 2. 视频数据块发送
通过 WebSocket 连接将视频块发送到后端，首先发送元数据包含时间戳、设备ID和视频块大小，然后直接发送二进制视频数据。

### 3. WebSocket 连接
连接到后端实时视频检测的 WebSocket 端点 `ws://localhost:8000/ws/live-video/{detectionDeviceId}`，用于实时传输视频数据。

### 4. 视频捕获和处理
使用 openAudio 和 openVideo 方法获取音频和视频流，将音频和视频流合并为一个新的媒体流，使用 RecordRTC 进行录制，然后发送到后端分析。

### 5. 视频文件测试
从前端的 video/train_number 文件夹加载视频文件，使用 fetch API 加载视频数据，然后通过 HTTP POST 请求发送到后端处理接口。

### 6. RecordRTC 完整头部数据原理
在实时视频检测功能中，RecordRTC 采用定时停止录制并重新开始的方法来确保每个视频块都包含完整的头部数据。通过设置 timeSlice 参数（例如60秒），然后显式调用 recorder.stopRecording()、recorder.getBlob() 和 recorder.startRecording()，确保每个发送给后端的 webm 视频块都是独立的、包含完整头部信息的文件，这样后端就可以独立处理每个视频块，而不需要依赖之前的头部信息。

## 系统要求

- 支持 HTML5 视频的现代 Web 浏览器
- 访问后端 API 服务器
- WebSocket 支持实时通信

## 安装

前端不需要特殊安装。它由静态文件组成，可以由任何 Web 服务器提供服务。

## 运行前端

### 使用 Python 内置服务器：
```bash
cd frontend
python -m http.server 8080
```

### 使用 Node.js：
```bash
cd frontend
npx serve
# 或安装并使用 http-server
npm install -g http-server
http-server
```

### 使用任何 Web 服务器：
使用您首选的 Web 服务器 (Apache、Nginx 等) 提供前端目录。

前端需要连接到后端 API 服务器，因此在使用界面之前请确保后端正在运行。

## 配置

前端在默认端点连接到后端 API，如有需要可在 JavaScript 文件中修改。请检查主 JavaScript 文件以获取 API 端点配置。