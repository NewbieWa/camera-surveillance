// 添加视频流处理相关的全局变量
var backendWebSocket = null;
var isProcessingVideo = false;

// 初始化视频流处理模块
function FUNC_init_videoStream(key) {
    LOG('FUNC_init_videoStream', key, true);
    
    // 初始化设备选择
    if (sdkclient.mConnected) {
        sdkclient.mClient.requestMsg2GatewayServer("getDevOnlineList", {}).then(resp => {
            const select = $('#deviceSelect');
            select.empty();
            select.append('<option value="">请选择设备</option>');
            
            if (resp.Content && Array.isArray(resp.Content)) {
                resp.Content.forEach(device => {
                    if (device.Status === 1) { // 只显示在线设备
                        select.append(`<option value="${device.DevId}">${device.DevId}</option>`);
                    }
                });
            }
        });
    }
    
    // 清空之前的处理结果
    $('#processingResults').empty();
    $('#analysisResults').empty();
}

// 连接到后端WebSocket服务
function connectToBackendWebSocket() {
    const backendUrl = 'ws://localhost:8000/ws/results';
    
    if (backendWebSocket) {
        backendWebSocket.close();
    }
    
    backendWebSocket = new WebSocket(backendUrl);
    
    backendWebSocket.onopen = function(event) {
        LOG('已连接到后端WebSocket服务', event);
        $('#streamStatus').append('<br>已连接到后端分析服务');
    };
    
    backendWebSocket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            displayAnalysisResult(data);
        } catch (e) {
            console.error('解析后端消息时出错:', e);
        }
    };
    
    backendWebSocket.onclose = function(event) {
        LOG('与后端WebSocket服务的连接已关闭', event);
    };
    
    backendWebSocket.onerror = function(error) {
        LOG('WebSocket连接错误', error);
        $('#streamStatus').append('<br>WebSocket连接错误: ' + error);
    };
}

// 显示分析结果
function displayAnalysisResult(result) {
    const resultsDiv = $('#processingResults');
    const timestamp = new Date().toLocaleTimeString();
    
    let resultHtml = '';
    if (result.type === 'vehicle_number') {
        resultHtml = `
          <div class="alert alert-info">
            <strong>[${timestamp}] 车号识别结果:</strong> ${result.result}
            ${result.vehicle_number ? `<br>识别到的车号: ${result.vehicle_number}` : ''}
          </div>`;
    } else if (result.type === 'anti_rolling') {
        const alertClass = result.success ? 'alert-success' : 'alert-warning';
        const statusText = result.success ? '成功' : '失败';
        resultHtml = `
          <div class="alert ${alertClass}">
            <strong>[${timestamp}] 防遛确认:</strong> ${result.result} (${statusText})
          </div>`;
    } else if (result.type === 'remove_rolling') {
        const alertClass = result.success ? 'alert-success' : 'alert-warning';
        const statusText = result.success ? '成功' : '失败';
        resultHtml = `
          <div class="alert ${alertClass}">
            <strong>[${timestamp}] 撤遛确认:</strong> ${result.result} (${statusText})
          </div>`;
    } else if (result.type === 'error') {
        resultHtml = `
          <div class="alert alert-danger">
            <strong>[${timestamp}] 错误:</strong> ${result.message}
          </div>`;
    }
    
    if (resultHtml) {
        resultsDiv.append(resultHtml);
        resultsDiv.scrollTop(resultsDiv[0].scrollHeight);
    }
    
    // 在结果展示区域显示详细信息
    displayDetailedResult(result);
}

// 显示详细结果
function displayDetailedResult(result) {
    const analysisDiv = $('#analysisResults');
    const timestamp = new Date().toLocaleTimeString();
    
    // 限制显示的结果数量，避免页面过长
    const maxResults = 10;
    if (analysisDiv.children().length >= maxResults) {
        analysisDiv.children().first().remove();
    }
    
    let detailHtml = '';
    if (result.type === 'vehicle_number') {
        detailHtml = `
          <div class="col-md-4">
            <div class="panel panel-info">
              <div class="panel-heading">
                <h3 class="panel-title">车号识别结果</h3>
              </div>
              <div class="panel-body">
                <p><strong>设备ID:</strong> ${result.device_id}</p>
                <p><strong>结果:</strong> ${result.result}</p>
                ${result.vehicle_number ? `<p><strong>车号:</strong> ${result.vehicle_number}</p>` : ''}
                <p><strong>时间:</strong> ${new Date(result.timestamp * 1000).toLocaleString()}</p>
              </div>
            </div>
          </div>`;
    } else if (result.type === 'anti_rolling') {
        const panelClass = result.success ? 'panel-success' : 'panel-warning';
        detailHtml = `
          <div class="col-md-4">
            <div class="panel ${panelClass}">
              <div class="panel-heading">
                <h3 class="panel-title">防遛确认结果</h3>
              </div>
              <div class="panel-body">
                <p><strong>设备ID:</strong> ${result.device_id}</p>
                <p><strong>结果:</strong> ${result.result}</p>
                <p><strong>时间:</strong> ${new Date(result.timestamp * 1000).toLocaleString()}</p>
              </div>
            </div>
          </div>`;
    } else if (result.type === 'remove_rolling') {
        const panelClass = result.success ? 'panel-success' : 'panel-warning';
        detailHtml = `
          <div class="col-md-4">
            <div class="panel ${panelClass}">
              <div class="panel-heading">
                <h3 class="panel-title">撤遛确认结果</h3>
              </div>
              <div class="panel-body">
                <p><strong>设备ID:</strong> ${result.device_id}</p>
                <p><strong>结果:</strong> ${result.result}</p>
                <p><strong>时间:</strong> ${new Date(result.timestamp * 1000).toLocaleString()}</p>
              </div>
            </div>
          </div>`;
    }
    
    if (detailHtml) {
        analysisDiv.append(detailHtml);
    }
}

// 开始传输视频流
$('#startStreamBtn').click(function() {
    const selectedDevice = $('#deviceSelect').val();
    if (!selectedDevice) {
        alert('请选择一个设备');
        return;
    }

    $('#streamStatus').text('正在启动视频流传输...');
    $('#startStreamBtn').hide();
    $('#stopStreamBtn').show();
    isProcessingVideo = true;

    // 连接到后端WebSocket服务
    connectToBackendWebSocket();

    // 发送开始处理请求到后端
    sendStartProcessingRequest(selectedDevice);
});

// 发送开始处理请求到后端
function sendStartProcessingRequest(deviceId) {
    // 这里应该通过HTTP请求通知后端开始处理指定设备的视频流
    fetch(`http://localhost:8000/video-stream/${deviceId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        LOG('后端响应', data);
        $('#streamStatus').text(`正在传输设备 ${deviceId} 的视频流到后端服务...`);
        
        // 模拟开始处理视频
        simulateVideoProcessing(deviceId);
    })
    .catch(error => {
        console.error('请求后端服务时出错:', error);
        LOG('请求后端服务时出错', error);
        $('#streamStatus').text(`错误: ${error.message}`);
    });
}

// 模拟视频处理过程
function simulateVideoProcessing(deviceId) {
    $('#streamStatus').append('<br>开始模拟视频处理...');
    
    // 模拟处理过程
    let progress = 0;
    const interval = setInterval(() => {
        if (!isProcessingVideo) {
            clearInterval(interval);
            return;
        }
        
        progress += 5;
        if (progress > 100) {
            progress = 100;
            clearInterval(interval);
        }
        
        $('#streamStatus').text(`正在处理设备 ${deviceId} 的视频流... ${progress}%`);
    }, 500);
    
    // 模拟发送一些测试结果
    setTimeout(() => {
        if (isProcessingVideo && backendWebSocket && backendWebSocket.readyState === WebSocket.OPEN) {
            // 模拟车号识别结果
            const vehicleResult = {
                "type": "vehicle_number",
                "device_id": deviceId,
                "result": "识别车号：ABC12345",
                "vehicle_number": "ABC12345",
                "frames": ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
                "timestamp": Date.now() / 1000
            };
            backendWebSocket.send(JSON.stringify(vehicleResult));
        }
    }, 2000);
    
    setTimeout(() => {
        if (isProcessingVideo && backendWebSocket && backendWebSocket.readyState === WebSocket.OPEN) {
            // 模拟防遛确认结果
            const antiRollingResult = {
                "type": "anti_rolling",
                "device_id": deviceId,
                "result": "防遛确认",
                "success": true,
                "frames": ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
                "timestamp": Date.now() / 1000
            };
            backendWebSocket.send(JSON.stringify(antiRollingResult));
        }
    }, 4000);
    
    setTimeout(() => {
        if (isProcessingVideo && backendWebSocket && backendWebSocket.readyState === WebSocket.OPEN) {
            // 模拟撤遛确认结果
            const removeRollingResult = {
                "type": "remove_rolling",
                "device_id": deviceId,
                "result": "撤遛未确认",
                "success": false,
                "frames": ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
                "timestamp": Date.now() / 1000
            };
            backendWebSocket.send(JSON.stringify(removeRollingResult));
        }
    }, 6000);
}

// 停止传输视频流
$('#stopStreamBtn').click(function() {
    $('#streamStatus').text('视频流传输已停止');
    $('#startStreamBtn').show();
    $('#stopStreamBtn').hide();
    isProcessingVideo = false;

    // 关闭WebSocket连接
    if (backendWebSocket) {
        backendWebSocket.close();
        backendWebSocket = null;
    }
    
    // 清空处理结果
    $('#processingResults').empty();
});