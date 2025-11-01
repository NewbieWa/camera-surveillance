const SLEEP = (delay) => new Promise((resolve) => setTimeout(resolve, delay));
const LOG = (utag, data, cls = false) => {
    var sdata = "";
    if (typeof data == 'object') {
        sdata = JSON.stringify(data);
    } else {
        sdata = data;
    }

    console.log("LOG [%s]%s %o", __KEY__, utag, data);

    if (cls) {
        $("#log").empty();
    }

    $("#log").append(`<p>[LOG] ${__KEY__} ${utag} ${sdata}</p>`);
};

const __KEY__ = 'SdkDemo';

var __GATEWAY_URL__ = null;
var __TOKEN__ = null;

/******************************************************
 * MCS8 JavaScript Client SDK 示例
 */
class SdkDemo {
    gatewayUrl = null;
    username = null;
    password = null;
    token = null;

    mClient = null;
    mConnected = false;
    mObserSet = new Map();

    constructor() {
        this.mClient = null;
        this.mConnected = false;
        this.mObserSet = new Map();
    }

    async __initClient(gatewayUrl, username, password, localVideo, localAudio) {

        //调度台地址：https://106.54.78.47:7715

        let url = new URL(gatewayUrl);

        let httpProxy = null;
        if (url.port == "") {
            httpProxy = `:443/gateway`
        } else {
            httpProxy = `:${url.port}/gateway`
        }

        LOG("connect url", url);

        let options = {
            //用户账号配置：支持调度台账号、企业管理员账号，一般使用调度台账号连接网关
            uid: username,                           //调度台用户名
            pwd: password,                           //调度台密码                   

            localVideo: localVideo,
            localAudio: localAudio,

            //网关连接参数配置，一般情况下使用默认配置即可，非必要不修改
            host: url.hostname,
            port: url.port,
            httpProxy: httpProxy,
            ssl: url.protocol.startsWith("https"),
            privateNet: false,
            encryType: 'v2',
            encryTime: Math.floor(Date.now() / 1000),
        }

        //创建实例
        this.mClient = new mcs8Client();

        //连接网关
        this.mClient.connect(options);

        LOG("connect", options);

        //注册回调，见onReceived
        this.mClient.on('OnManage', this.onReceived.bind(this));
    }

    /****************************************************** */
    //SDK 方法

    /**
     * 连接网关
     * @param {*} gatewayUrl 网关地址
     * @param {*} username 用户名，调度台账号、企业账号，一般为调度台账号
     * @param {*} password 密码
     * @param {*} localVideo 本地Video元素
     * @param {*} localAudio 本地Audio元素
     */
    async connect(gatewayUrl, username, password, localVideo, localAudio) {

        try {
            var url = new URL(gatewayUrl);
        } catch (error) {
            alert('网关地址错误！');
            return;
        }

        __GATEWAY_URL__ = gatewayUrl;

        this.gatewayUrl = gatewayUrl;
        this.username = username;

        this.__initClient(gatewayUrl, username, password, localVideo, localAudio);

        var wait = 5;
        while (!this.mConnected) {
            await SLEEP(500);
            if ((wait--) < 0) {
                break;
            }
        }

        await SLEEP(500);
    }

    /**
     * 关闭连接
     */
    async close() {
        this.mConnected = false;
        if (this.mClient) {
            this.mClient.close();
            this.mClient = null;
        }
    }

    /**
     * 消息回调
     * @param {*} msg 
     * @returns 
     */
    async onReceived(msg) {

        if (this.mClient == null) {
            return;
        }

        LOG("onReceived", msg.method);

        if (msg.method == 'ConnecteInfo') {
            //连接成功
            __TOKEN__ = msg.data.token;
            this.mConnected = true;
            return;
        } else if (msg.method == 'responseConnectGateway') {
            if (msg.errCode == 200) {
                //ok
            } else if (msg.errCode == 500) {
                alert('连接服务器失败');
                this.close();
            }
            else {
                alert('鉴权失败！用户名或密码错误，或无权限。');
                this.close();
            }
        } else if (msg.method == 'JoinRoomAndProduct') {
            /*创建群组，调度台端一般为收到群组邀请，如设备端发起呼叫
            msg.data = {
                "roomId": "20315664", //组Id
                "TalkGroupType": 5,   //组类型，4：集群对讲组，5：视频组，6：语音组
                "creatorId": "test2", //创建者设备Id，即呼叫方
                "devList": []         //成员
            }*/
        } else if (msg.method == 'joinRoom') {

        } else if (msg.method == 'newPeer') {
            //进入组
        } else if (msg.method == 'peerClosed') {
            //退出组
        } else if (msg.method == 'noAgreeIntoGroup') {
            //拒绝进入组
        } else if (msg.method == 'meetingOut') {
            //解散组
        } else if (msg.method == 'newTalker') {
            //申请发言（成功，正在发言）
        } else if (msg.method == 'freeTalker') {
            //释放发言
        } else if (msg.method == 'gpsUpload') {
            /*设备GPS消息上报，坐标类型：WGS84(大地坐标)：
            msg.data = {
                "devId": "test1", //设备Id
                "gpsTime": "2022-10-24 14:28:37", //定位时间 
                "lat": 22.57696333333333, //维度，WGS84(大地坐标)
                "lng": 113.91693500000001, //经度
                "accuracy": 7, //精度（米）
                "speed": 0, //速度（米）
                "direct": 0, //方向
                "netWorkType": 1, //网络类型：1WIFI，2移动网络   
                "totalSize": 50319328, //存储容量（字节）
                "useSize": 4209568, //已用容量
                "battery": 71, //电量（%）
            }*/
        } else if (msg.method == 'DeviceStatus') {
            /*设备状态消息上报，如上线、下线：
            msg.data = {
                "Content": [
                    {
                        "DevId": "test1", //设备Id
                        "Status": 0 //设备状态：0离线，1上线
                    }
                ]
            }
            */
        }
        else if (msg.method == 'AlarmUpload') {
            /*设备报警消息上报，如SOS：
            msg.data = {
                "devId": "test1", //设备Id
                "enterId": 20000000, //企业Id
                "groupId": 30000000, //组Id
                "peopleNo": "000000", //人员编号
                "workNo": "8600021935078769", //工单编号 
                "alarmType": 2, //报警类型，见《1.8.报警信息上报》
                "alarmTime": "2022-10-24 15:36:36", //报警时间
                "alarmDesc": "sos", //报警描述
                "status": 1, //报警状态：0无（无开始和结束标识），1开始报警，2结束报警
                "GPSModel": { //报警位置
                    "gpsTime": "1970-01-01 08:00:00",
                    "lat": "0.0",
                    "lng": "0.0",
                    "netWorkType": 1
                },
            }*/
        }
        else if (msg.method == 'logoutByOtherLogin') {
            //踢出（异地登录）          
            this.close();
        } else {
            return;
        }

        LOG("onReceived", msg);

        this.notifyAllObserver(msg);
    }

    /**
     * 发送消息》网关
     * @param {*} method 命令字
     * @param {*} data 消息数据体
     * @returns 
     */
    async requestMsg2GatewayServer(method, data) {
        LOG(`requestMsg2GatewayServer method=${method}`, data);

        let r = await this.mClient.requestMsg2GatewayServer(method, data);
        LOG(`requestMsg2GatewayServer method=${method} resp=`, r);

        return r;
    }

    /****************************************************** */
    //SDK & 观察者封装

    addObserver(key, fn) {
        this.mObserSet.set(key, fn);
    }

    removeObserver(key) {
        this.mObserSet.delete(key);
    }

    notifyAllObserver(request) {
        for (var [key, fn] of this.mObserSet) {
            fn.call(this, request);
        }
    }
}

/******************************************************
 * pages FUNC
 */
var sdkclient = new SdkDemo();

/**
 * 初始化模块：
 * @param {*} key 
 */
function FUNC_init_quick(key) {
    LOG('FUNC_init_quick', key, true);
}

/**
 * 初始化模块：
 * @param {*} key 
 */
function FUNC_init_connect(key) {
    LOG('FUNC_init_connect', key, true);
}

/**
 * 初始化模块：获取在线设备列表
 * @param {*} key 
 */
function FUNC_init_getDevOnlineList(key) {
    //LOG('FUNC_init_getDevOnlineList', key, (key == 'getDevOnlineList'));

    if (sdkclient.mConnected) {
        sdkclient.mClient.requestMsg2GatewayServer("getDevOnlineList", {}).then(resp => {
            LOG('getDevOnlineList', resp);

            /*获取在线设备列表，Status：状态，0离线，1在线（仅返回在线设备） ：
            resp.Content = [
                {
                    "DevId": "pc1",
                    "Status": 1
                },
                {
                    "DevId": "test1",
                    "Status": 1
                }
            ]*/

            var data = { list: resp.Content };
            var html = template(`tpl_${key}`, data);
            document.getElementById(`tpl_${key}_content`).innerHTML = html;
        })
    }
}

/**
 * 初始化模块：获取设备列表（全部）
 * @param {*} key 
 */
async function FUNC_init_getDevList(key) {
    LOG('FUNC_init_getDevList', key, true);

    if (sdkclient.mConnected) {

        var devStatus = await sdkclient.mClient.requestMsg2GatewayServer("getDevOnlineList", {});

        var url = `${__GATEWAY_URL__.replace("gateway", "")}/api/v1/ext/DevTree?token=${__TOKEN__}`;

        $.ajax({
            headers: {
                "token": __TOKEN__
            },
            type: "GET",
            url: url,
            contentType: "application/json",
            success: function (resp) {
                var data = [];

                if (resp.result == 0 || resp.result == 200) {

                    for (const item of resp.content) {

                        var pId = item.pid;
                        if (item.type == 1 && pId == 0) { //type=1企业
                        }
                        if (item.type == 2 && pId == 0) { //type=2固定组
                            var findEnter = resp.content.find(p => p.type == 1 && p.id == item.data.enterId);
                            if (findEnter) {
                                pId = findEnter.id;
                            }
                        }
                        if (item.type == 3 && pId == 0) { //type=3终端设备
                            var findEnter = resp.content.find(p => p.type == 1 && p.id == item.data.enterId);
                            if (findEnter) {
                                pId = findEnter.id;
                            }
                        }

                        var name = item.text;
                        if (item.type == 1) {
                            name = '[企业]' + name
                        }
                        else if (item.type == 2) {
                            name = '[固定组]' + name
                        }
                        else if (item.type == 3) {
                            if (item.data.deviceType == '2') {
                                name = '[调度台]' + name;
                            } else {
                                name = '[设备]' + name;
                            }
                            var find = devStatus.Content.find(p => p.DevId == item.data.deviceId);
                            if (find) {
                                item.data.status = 1;
                                name = name + '(在线)';
                            } else {
                                item.data.status = 0;
                                name = name + '(离线)';
                            }
                        }

                        data.push({
                            ...item,
                            pId,
                            name,
                            open: (item.type == 1)
                        });

                        //多路处理
                        if (item.type == 3 && item.data.deviceType == '5' || item.data.deviceType == '11') {
                            if (Array.isArray(item.extras)) {
                                for (const devCh of item.extras) {
                                    data.push({
                                        ...item,
                                        id: devCh.id,
                                        pId: item.id,
                                        name: '[通道]' + devCh.name,
                                        channelId: devCh.code,
                                        channelName: devCh.name
                                    });
                                }
                            }
                        }
                    }

                    $.fn.zTree.init($("#devTree"), {
                        view: {
                        },
                        data: {
                            simpleData: {
                                enable: true
                            }
                        }
                    }, data);

                    var text = `\r\n请求地址：\r\n${url}\r\n响应数据：\r\n${JSON.stringify(resp)}`
                    LOG(key, text, true);
                }
            }
        });
    }
}

/**
 * 初始化模块：实时视频/声音监听
 * @param {*} key 
 */
function FUNC_init_openVideo(key) {

    LOG('FUN_init_openVideo', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：双向视频通话
 * @param {*} key 
 */
function FUNC_init_CreateP2pMediaGroup(key) {

    LOG('FUNC_init_CreateP2pMediaGroup', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：双向语音通话
 * @param {*} key 
 */
function FUNC_init_CreateP2pMediaGroup6(key) {

    LOG('FUNC_init_CreateP2pMediaGroup6', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：接听设备视频呼叫
 * @param {*} key 
 */
function FUNC_init_add2MediaGroup(key) {

    LOG('FUNC_init_add2MediaGroup', key, true);

    if (sdkclient.mConnected) {

        $("#tpl_add2MediaGroup_content").html("请在设备端发起呼叫");

        //被动呼叫，包括视频呼叫、语音呼叫，一般流程为：
        //1、在回调里监听 [JoinRoomAndProduct] 命令字，此命令字表示来自设备端的呼叫；
        //2、加入群组：add2MediaGroup
        //3、加入群组后，然后监听[JoinRoom]，并关联HTML音频、视频元素

        //监听回调消息类型，见onReceived->method：JoinRoomAndProduct说明
        sdkclient.addObserver('add2MediaGroup', msg => {
            if (msg.method == 'JoinRoomAndProduct') {
                var data = { list: [msg.data] };
                var html = template(`tpl_${key}`, data);
                document.getElementById(`tpl_${key}_content`).innerHTML = html;
            } else if (msg.method === 'joinRoom') {
                //关联音频和视频HTML元素
                for (const peer of msg.data.peers) {

                    //关联HTML Audio元素
                    sdkclient.mClient.addShowObject({
                        groupId: msg.data.groupId,
                        kind: 'audio',
                        devId: peer.id,
                        showObj: document.getElementById(`remoteAudio${peer.id}`)
                    });

                    if (msg.data.groupType == 5) { //视频组，关联HTML Video元素
                        sdkclient.mClient.addShowObject({
                            groupId: msg.data.groupId,
                            kind: 'video',
                            devId: peer.id,
                            showObj: document.getElementById(`remoteVideo${peer.id}`)
                        });
                    }
                }
            }
        })
    }
}

/**
 * 初始化模块：接听设备语音呼叫
 * @param {*} key 
 */
function FUNC_init_add2MediaGroup6(key) {

    LOG('FUNC_init_add2MediaGroup6', key, true);

    if (sdkclient.mConnected) {

        $("#tpl_add2MediaGroup6_content").html("请在设备端发起呼叫");

        //监听回调消息类型，见onReceived->method：JoinRoomAndProduct说明
        sdkclient.addObserver('add2MediaGroup6', msg => {
            if (msg.method == 'JoinRoomAndProduct') {
                var data = { list: [msg.data] };
                var html = template(`tpl_${key}`, data);
                document.getElementById(`tpl_${key}_content`).innerHTML = html;
            } else if (msg.method === 'joinRoom') {
                for (const peer of msg.data.peers) {
                    sdkclient.mClient.addShowObject({
                        groupId: msg.data.groupId,
                        kind: 'audio',
                        devId: peer.id,
                        showObj: document.getElementById(`remoteAudio${peer.id}`)
                    });
                }
            }
        })
    }
}

/**
 * 初始化模块：多人语音通话
 * @param {*} key 
 */
function FUNC_init_CreateTempMediaGroup(key) {

    LOG('FUNC_init_CreateTempMediaGroup', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：向设备喊话
 * @param {*} key 
 */
function FUNC_init_startTalk(key) {

    LOG('FUNC_init_startTalk', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：获取实时位置
 * @param {*} key 
 */
function FUNC_init_getGps(key) {

    LOG('FUNC_init_getGps', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：获取设备参数
 * @param {*} key 
 */
function FUNC_init_getDeviceInfo(key) {

    LOG('FUNC_init_getDeviceInfo', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：GPS消息上报
 * @param {*} key 
 */
function FUNC_init_gpsUpload(key) {

    LOG('FUNC_init_gpsUpload', key, true);

    if (sdkclient.mConnected) {
        $("#tpl_gpsUpload_content").html("等待消息上报");

        //监听回调消息类型，见onReceived->method：gpsUpload说明
        sdkclient.addObserver('gpsUpload', msg => {
            if (msg.method == 'gpsUpload') {
                $("#tpl_gpsUpload_content").append(`<div class="alert alert-success">${JSON.stringify(msg.data)}</div>`);
            }
        })
    }
}

/**
 * 初始化模块：设备上下线消息上报
 * @param {*} key 
 */
function FUNC_init_DeviceStatus(key) {

    LOG('FUNC_init_DeviceStatus', key, true);

    if (sdkclient.mConnected) {
        $("#tpl_DeviceStatus_content").html("等待消息上报");

        //监听回调消息类型，见onReceived->method：DeviceStatus说明
        sdkclient.addObserver('DeviceStatus', msg => {
            if (msg.method == 'DeviceStatus') {
                $("#tpl_DeviceStatus_content").append(`<div class="alert alert-success">${JSON.stringify(msg.data)}</div>`);
            }
        })
    }
}

/**
 * 初始化模块：设备SOS报警消息上报
 * @param {*} key 
 */
function FUNC_init_AlarmUpload(key) {

    LOG('FUNC_init_AlarmUpload', key, true);

    if (sdkclient.mConnected) {
        $("#tpl_AlarmUpload_content").html("等待消息上报");

        //监听回调消息类型，见onReceived->method：AlarmUpload说明
        sdkclient.addObserver('AlarmUpload', msg => {
            if (msg.method == 'AlarmUpload') {
                $("#tpl_AlarmUpload_content").append(`<div class="alert alert-success">${JSON.stringify(msg.data)}</div>`);
            }
        })
    }
}

/**
 * 初始化模块：下发录像指令
 * @param {*} key 
 */
function FUNC_init_startRecord(key) {

    LOG('FUNC_init_startRecord', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：下发工单消息
 * @param {*} key 
 */
function FUNC_init_sendWorkNo(key) {

    LOG('FUNC_init_sendWorkNo', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 初始化模块：下发文本消息
 * @param {*} key 
 */
function FUNC_init_sendIM(key) {

    LOG('FUNC_init_sendIM', key, true);

    FUNC_init_getDevOnlineList(key);
}

/**
 * 连接网关
 */
function FUNC_connect() {
    var gatewayUrl = $("#txtGatewayUrl").val();
    var username = $("#txtUsername").val();
    var password = $("#txtPassword").val();

    gatewayUrl = gatewayUrl.trim();
    username = username.trim();
    password = password.trim();

    if (gatewayUrl == "" || username == "" || password == "") {
        alert("请输入有效的网关地址、账号、密码！如无账号，请联系业务经理。");
        return;
    }

    if (sdkclient.mConnected) {
        sdkclient.close();
        alert("已断开连接");
        $("#btnConnect").text("连接网关");
    } else {
        sdkclient.connect(gatewayUrl, username, password, document.getElementById("localVideo"), document.getElementById("localAudio")).then(resp => {
            if (sdkclient.mConnected) {
                alert("连接成功");
                $("#btnConnect").text("断开连接");
            } else {
                $("#btnConnect").text("重新连接");
            }
        })
    }
}

/**
 * 打开实时视频
 * @param {*} devId 设备Id
 * @param {*} channelId 通道号（非多通道设备为null）
 */
async function FUNC_openVideo(devId, channelId) {
    var remoteVideo = document.getElementById(`remoteVideo${devId}`);
    var resp = await sdkclient.mClient.openVideo(devId, remoteVideo, channelId, null);//设备Id,HTMLVideo对象,设备通道（可为null），服务器Id(一般不需要使用)

    LOG('openVideo', resp);
}

/**
 * 关闭实时视频
 * @param {*} devId 设备Id
 * @param {*} channelId 通道号（非多通道设备为null）
 */
async function FUNC_closeVideo(devId, channelId) {
    var resp = await sdkclient.mClient.closeVideo(devId, channelId);//设备Id,设备通道（可为null），服务器Id(一般不需要使用)

    LOG('closeVideo', resp);
}

/**
 * 打开声音监听
 * @param {*} devId 设备Id
 * @param {*} channelId 通道号（非多通道设备为null）
 */
async function FUNC_openAudio(devId, channelId) {
    var remoteAudio = document.getElementById(`remoteAudio${devId}`);
    var resp = await sdkclient.mClient.openAudio(devId, remoteAudio, channelId);//设备Id,HTMLAudio对象,设备通道（可为null），服务器Id(一般不需要使用)

    LOG('openAudio', resp);
}

/**
 * 关闭声音监听
 * @param {*} devId 设备Id
 * @param {*} channelId 通道号（非多通道设备为null）
 */
async function FUNC_closeAudio(devId, channelId) {
    var resp = await sdkclient.mClient.closeAudio(devId, channelId);//设备Id,设备通道（可为null），服务器Id(一般不需要使用)

    LOG('closeAudio', resp);
}

var __randomGroupIdMap = {};

/**
 * 获取通话组Id：不重复即可
 * @param {*} devId 
 * @returns 
 */
function __FUNC_CreateRandomGroupId(devId, groupId = 0) {
    if (devId == undefined) {
        devId = "temp";
    }

    if (groupId > 0) {
        __randomGroupIdMap[devId] = groupId;
    } else {
        __randomGroupIdMap[devId] = Date.parse(new Date()).toString();
    }

    return __randomGroupIdMap[devId];
}

/**
 * 创建双向视频通话组
 * @param {*} devId 
 */
async function FUNC_CreateP2pMediaGroup(devId) {
    var groupId = __FUNC_CreateRandomGroupId(devId);
    var groupType = 5; //组类型，4：集群对讲组，5：视频组，6：语音组

    if (await sdkclient.mClient.checkInputDevice(groupType) == 404) {
        alert('该功能需要麦克风（USB耳麦）、摄像头支持！');
        return;
    }

    var devModel = { kind: 'video', devId, showObj: document.getElementById(`remoteVideo${devId}`) }
    var resp = await sdkclient.mClient.CreateP2pMediaGroup(groupId, groupType, devModel);

    LOG('CreateP2pMediaGroup', resp);

    //监听进入组回调，关联音频元素，见onReceived说明
    sdkclient.addObserver('CreateP2pMediaGroup', msg => {
        if (msg.method == 'newPeer') {
            sdkclient.mClient.addShowObject({
                groupId: __randomGroupIdMap[devId],
                kind: 'audio',
                devId: msg.data.id,
                showObj: document.getElementById(`remoteAudio${msg.data.id}`)
            });
        }
    })
}

/**
 * 创建双向语音通话组
 * @param {*} devId 
 */
async function FUNC_CreateP2pMediaGroup6(devId) {
    var groupId = __FUNC_CreateRandomGroupId(devId);
    var groupType = 6; //组类型，4：集群对讲组，5：视频组，6：语音组

    if (await sdkclient.mClient.checkInputDevice(groupType) == 404) {
        alert('该功能需要麦克风（USB耳麦）支持！');
        return;
    }

    var devModel = { kind: 'audio', devId, showObj: document.getElementById(`remoteAudio${devId}`) }
    var resp = await sdkclient.mClient.CreateP2pMediaGroup(groupId, groupType, devModel);

    LOG('CreateP2pMediaGroup', resp);
}

/**
 * 接听设备呼叫
 * @param {*} devId 
 */
async function FUNC_add2MediaGroup(groupId, groupType) {

    if (await sdkclient.mClient.checkInputDevice(groupType) == 404) {
        alert('该功能需要麦克风（USB耳麦）、摄像头支持！');
        return;
    }

    sdkclient.mClient.add2MediaGroup({
        groupId: groupId,
        talkGroupType: parseInt(groupType),
        temGroupType: 0,
        isCreator: 0,
        istalk: true
    });
}

/**
 * 创建多人语音通话组（集群对讲）
 * @param {*} groupKey 
 * @returns 
 */
async function FUNC_CreateTempMediaGroup(groupKey) {

    var devList = [];
    $("#CreateTempMediaGroup").find("input:checkbox:checked").each((i, item) => {
        devList.push(
            {
                kind: 'audio',
                devId: item.value,
                showObj: document.getElementById(`remoteAudio${item.value}`)
            }
        );
    });

    if (devList.length == 0) {
        alert("未选择设备");
        return;
    }

    var groupId = __FUNC_CreateRandomGroupId(groupKey);
    var groupType = 4; //组类型，4：集群对讲组，5：视频组，6：语音组

    if (await sdkclient.mClient.checkInputDevice(groupType) == 404) {
        alert('该功能需要麦克风（USB耳麦）支持！');
        return;
    }

    var resp = await sdkclient.mClient.CreateTempMediaGroup(groupId, groupType, devList);

    LOG('CreateTempMediaGroup', resp);
}

/**
 * 申请发言权（排他性）
 * @param {*} groupKey 
 */
async function FUNC_applyTalk(groupKey) {

    var resp = await sdkclient.mClient.applyTalk(__randomGroupIdMap[groupKey]);

    LOG('applyTalk', resp);

    if (resp && resp.status === 1) {
        alert("请发言！说点什么呢...");
    } else {
        alert("~打断别人说话是不礼貌的行为~");
    }
}

/**
 * 释放发言权
 * @param {*} groupKey 
 */
async function FUNC_freeTalker(groupKey) {
    await sdkclient.mClient.freeTalker(__randomGroupIdMap[groupKey]);
}

/**
 * 关闭通话组
 */
async function FUNC_closeGroup(devId, groupId = 0) {

    sdkclient.removeObserver("CreateP2pMediaGroup");

    if (groupId == 0) {
        groupId = __randomGroupIdMap[devId]
    }

    var resp = await sdkclient.mClient.closeGroup(groupId);

    LOG('closeGroup', resp);
}

/**
 * 开始喊话
 * @param {*} devId 
 * @param {*} channelId 
 */
async function FUNC_startTalk(devId, channelId) {

    if (await sdkclient.mClient.checkInputDevice() == 404) {
        alert('该功能需要麦克风（USB耳麦）支持！');
        return;
    }

    var resp = await sdkclient.mClient.startTalk(devId, channelId);

    LOG('startTalk', resp);
}

/**
 * 停止喊话
 * @param {*} devId 
 * @param {*} channelId 
 */
async function FUNC_stopTalk(devId, channelId) {
    var resp = await sdkclient.mClient.stopTalk();

    LOG('stopTalk', resp);
}

/**
 * 获取实时位置
 * @param {*} devId 
 */
async function FUNC_getGps(devId) {
    sdkclient.mClient.requestMsg2GatewayServer('getGps', { devId }).then(resp => {
        LOG('getGps', resp);

        //消息类型，见onReceived->method：gpsUpload说明

        if ($(`#txt_getGps_${devId}`).length > 0) {
            $(`#txt_getGps_${devId}`).val(JSON.stringify(resp));
        } else {
            alert(JSON.stringify(resp));
        }

    })
}

/**
 * 获取设备参数
 * @param {*} devId 
 */
async function FUNC_getDeviceInfo(devId) {
    sdkclient.mClient.requestMsg2GatewayServer('getDeviceInfo', { devId }).then(resp => {
        LOG('getDeviceInfo', resp);

        //"network": 1, //网络类型：1WIFI，2移动网络   
        //"recording": 2, //录像状态：1正在录像，2未录像
        //"totalSize": 50319328, //存储容量（字节）
        //"useSize": 4209568, //已用容量
        //"battery": 71, //电量（%）
        //"lat": 22.57688333333333, //维度，WGS84(大地坐标)
        //"lng": 113.91682, //经度，WGS84(大地坐标)
        //"hardware": "N6F26Q test-keys", //固件版本
        //"version": "1.5.44", //APP版本
        //"peopleNo": "000000", //人员编号
        //"workNo": "8600021935078769" //工单号

        if ($(`#txt_getDeviceInfo_${devId}`).length > 0) {
            $(`#txt_getGps_${devId}`).val(JSON.stringify(resp));
        } else {
            alert(JSON.stringify(resp));
        }
    })
}

/**
 * 开启录像
 * @param {*} devId 
 */
async function FUNC_startRecord(devId) {
    sdkclient.mClient.requestMsg2GatewayServer('startRecord', { devId: devId, peopleNo: "", workNo: "R123456", storType: 0 }).then(resp => {
        LOG('startRecord', resp);

        //devId: 设备Id 
        //peopleNo: 人员号，可选
        //workNo: 工单号，可选，当不为空时按此工单录像
        //storType: 0设备录像
    })
}

/**
 * 停止录像
 * @param {*} devId 
 */
async function FUNC_stopRecord(devId) {
    sdkclient.mClient.requestMsg2GatewayServer('stopRecord', { devId: devId, storType: 0 }).then(resp => {
        LOG('stopRecord', resp);

        //devId: 设备Id     
        //storType: 0设备录像
    })
}

/**
 * 下发工单消息
 * @param {*} devId 
 */
async function FUNC_sendWorkNo(devId, workNo) {

    if (workNo == '') {
        alert('工单号不能为空');
        return;
    }

    sdkclient.mClient.requestMsg2GatewayServer('sendWorkNo', { devList: [devId], peopleNo: "", workNo: workNo, des: "这是一个测试工单" }).then(resp => {
        LOG('sendWorkNo', resp);

        //devList: 设备Id，支持多个 
        //peopleNo: 人员号，可选
        //workNo: 工单号
        //des: 备注
    })
}

/**
 * 下发文本消息
 * @param {*} devId 
 */
async function FUNC_sendIM(devId, content, tts) {

    if (content == '') {
        alert('内容不能为空');
        return;
    }

    var arr = CryptoJS.enc.Utf8.parse(content);
    var base64content = CryptoJS.enc.Base64.stringify(arr);

    LOG('sendIM', base64content);

    sdkclient.mClient.requestMsg2GatewayServer('sendIM',
        {
            "scene": "tempTeam",
            "to": [
                devId
            ],
            "sendUserId": "pc1",
            "time": "2022-10-28 17:21:45",
            "fromClientType": "Web",
            "target": "pc12022102817",
            "type": tts == true ? 'tts' : 'text',
            "content": base64content
        }
    ).then(resp => {
        LOG('sendIM', resp);

        //devList: 设备Id，支持多个 
        //peopleNo: 人员号，可选
        //workNo: 工单号
        //des: 备注
    })
}


/******************************************************
 * demo.html
 */

/**
 * 初始化模块：第一个例子
 * @param {*} key 
 */
async function FUNC_init_demo(key) {

    LOG('FUNC_init_demo', key, true);

    //获取在线设备
    var devStatus = await sdkclient.mClient.requestMsg2GatewayServer("getDevOnlineList", {});

    //获取设备树（并根据[devStatus]修正设备状态）
    $.ajax({
        headers: {
            "token": __TOKEN__
        },
        type: "GET",
        url: `${__GATEWAY_URL__.replace("gateway", "")}/api/v1/ext/DevTree`,
        contentType: "application/json",
        success: function (resp) {
            var data = [];
            if (resp.result == 0 || resp.result == 200) {

                for (const item of resp.content) {

                    var pId = item.pid;
                    if (item.type == 1 && pId == 0) { //type=1企业
                    }
                    if (item.type == 2 && pId == 0) { //type=2固定组
                        var findEnter = resp.content.find(p => p.type == 1 && p.id == item.data.enterId);
                        if (findEnter) {
                            pId = findEnter.id;
                        }
                    }
                    if (item.type == 3 && pId == 0) { //type=3终端设备
                        var findEnter = resp.content.find(p => p.type == 1 && p.id == item.data.enterId);
                        if (findEnter) {
                            pId = findEnter.id;
                        }
                    }

                    var name = item.text;
                    if (item.type == 1) {
                        name = '[企业]' + name
                    }
                    else if (item.type == 2) {
                        name = '[固定组]' + name
                    }
                    else if (item.type == 3) {
                        if (item.data.deviceType == '2') {
                            name = '[调度台]' + name;
                        } else {
                            name = '[设备]' + name;
                        }
                        var find = devStatus.Content.find(p => p.DevId == item.data.deviceId);
                        if (find) {
                            item.data.status = 1;
                            name = name + '(在线)';
                        } else {
                            item.data.status = 0;
                            name = name + '(离线)';
                        }
                    }

                    data.push({
                        ...item,
                        pId,
                        name,
                        open: (item.type == 1)
                    });

                    //多路处理
                    if (item.type == 3 && item.data.deviceType == '5' || item.data.deviceType == '11') {
                        if (Array.isArray(item.extras)) {
                            for (const devCh of item.extras) {
                                data.push({
                                    ...item,
                                    id: devCh.id,
                                    pId: item.id,
                                    name: '[通道]' + devCh.name,
                                    channelId: devCh.code,
                                    channelName: devCh.name
                                });
                            }
                        }
                    }
                }

                $.fn.zTree.init($("#devTree"), {
                    view: {
                    },
                    data: {
                        simpleData: {
                            enable: true
                        }
                    },
                    callback: {
                        onClick: function (a, b, c) {
                            console.log('zTree %o', c);

                            if (c.type == 1 || c.type == 2) {
                                var zTree = $.fn.zTree.getZTreeObj("devTree");
                                zTree.expandNode(c);
                                return true;
                            }

                            var tpl = '';

                            var deviceTypeDesc = '其它';
                            if (c.data.deviceType == "1") {
                                deviceTypeDesc = "视频终端";
                                tpl = '1';
                            }
                            if (c.data.deviceType == "2") {
                                deviceTypeDesc = "调度台";
                            }
                            if (c.data.deviceType == "5") {
                                deviceTypeDesc = "多通道视频终端";
                                if (c.channelId) {
                                    tpl = '5';
                                }
                            }
                            if (c.data.deviceType == "11") {
                                deviceTypeDesc = "GB28181视频终端";
                                if (c.channelId) {
                                    tpl = '5';
                                }
                            }

                            if (c.data.status == 0) {
                                tpl = '';
                            }

                            var data = {
                                list: [
                                    {
                                        ...c.data,
                                        deviceTypeDesc,
                                        statusDesc: c.data.status == 1 ? '在线' : '离线',
                                        channelId: c.channelId,
                                        channelName: c.channelName
                                    }
                                ]
                            };


                            var html = template(`tpl_${key}_${tpl}`, data);
                            document.getElementById(`tpl_${key}_content`).innerHTML = html;
                        },
                    }
                }, data);
            }
        }
    });
}
