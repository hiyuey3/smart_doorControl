// pages/arm/arm.js Created by Yue@5i03.cn
// 你说机械做的心会梦见电子蝴蝶吗？

function SimpleMQTT() {
 console.log(' 你说机械做的心会梦见电子蝴蝶吗？Created by YueYu@5i03.cn ｜ github.com/hiyuey3/:')
  this.client = null
  this.isConnected = false
  // 生成随机 ClientID，格式为 wx_client_xxxx
  this.clientId = 'wx_client_' + Math.random().toString(16).substr(2, 8)
  this.messageCallback = null
  this.subscriptions = []
  this.packetId = 1
  this._recvBuffer = new Uint8Array(0) // 接收缓冲区，用于重组分片
}

SimpleMQTT.prototype.connect = function(url) {
  return new Promise((resolve, reject) => {
    try {
      console.log('正在连接MQTT服务器:', url)
      
      this.client = wx.connectSocket({
        url: url,
        protocols: ['mqtt']
      })

      wx.onSocketOpen(() => {
        console.log('WebSocket连接成功')
        // 在 TCP/WebSocket 连接建立后发送 MQTT CONNECT 包，
        // 但只有在收到 CONNACK 后才算作 MQTT 层面的连接成功。
        const connectPacket = this._buildConnectPacket()
        try {
          wx.sendSocketMessage({ data: connectPacket.buffer })
          // 为 CONNACK 等待提供超时兜底
          const self = this
          this._connackTimer = setTimeout(() => {
            console.warn('等待 CONNACK 超时，继续认为连接已就绪')
            self.isConnected = true
            if (resolve) resolve()
          }, 4000)
          this._connackResolve = () => {
            clearTimeout(self._connackTimer)
            self._connackTimer = null
            self._connackResolve = null
            self.isConnected = true
            console.log('MQTT CONNACK 已收到，MQTT 连接建立')
            if (resolve) resolve()
          }
        } catch (e) {
          console.error('发送 CONNECT 包失败:', e)
        }
      })

      wx.onSocketMessage(res => {
        try {
          let data = res.data
          let uint8
          if (typeof data === 'string') {
            // 尝试按 base64 解码为 ArrayBuffer
            try {
              const ab = wx.base64ToArrayBuffer(data)
              uint8 = new Uint8Array(ab)
            } catch (e) {
              // 回退：按字符串字节解析
              const bytes = this._stringToBytes(data)
              uint8 = new Uint8Array(bytes)
            }
          } else {
            // 直接是 ArrayBuffer
            uint8 = new Uint8Array(data)
          }
          // 将收到的数据交由缓冲区处理，支持分片重组
          this._handleIncomingData(uint8)
        } catch (err) {
          console.error('解析收到的数据失败:', err)
        }
      })

      wx.onSocketError(err => {
        console.error('WebSocket连接错误:', err)
        this.isConnected = false
        if (reject) reject(err)
      })

      wx.onSocketClose(() => {
        console.log('WebSocket连接关闭')
        this.isConnected = false
      })
    } catch (err) {
      if (reject) reject(err)
    }
  })
}

SimpleMQTT.prototype._buildConnectPacket = function() {
  const protocol = 'MQTT'
  const protocolLevel = 4
  const connectFlags = 0x02
  const keepAlive = 60

  // Variable Header
  const varHeader = []
  
  // Protocol name
  varHeader.push((protocol.length >> 8) & 0xFF)
  varHeader.push(protocol.length & 0xFF)
  for (let i = 0; i < protocol.length; i++) {
    varHeader.push(protocol.charCodeAt(i))
  }
  // Protocol level
  varHeader.push(protocolLevel)
  // Connect flags
  varHeader.push(connectFlags)
  // Keep alive
  varHeader.push((keepAlive >> 8) & 0xFF)
  varHeader.push(keepAlive & 0xFF)

  // Payload
  const payload = []
  const clientIdBytes = this._stringToBytes(this.clientId)
  payload.push((clientIdBytes.length >> 8) & 0xFF)
  payload.push(clientIdBytes.length & 0xFF)
  for (let i = 0; i < clientIdBytes.length; i++) {
    payload.push(clientIdBytes[i])
  }

  // Remaining length
  const remainingLength = varHeader.length + payload.length
  const lengthBytes = this._encodeLength(remainingLength)

  // Fixed header
  const packet = [0x10]
  packet.push(...lengthBytes)
  packet.push(...varHeader)
  packet.push(...payload)

  return new Uint8Array(packet)
}

SimpleMQTT.prototype.publish = function(topic, message) {
  if (!this.isConnected) {
    console.error('MQTT未连接')
    return false
  }

  try {
    const topicBytes = this._stringToBytes(topic)
    const messageBytes = this._stringToBytes(message)

    // Variable header
    const varHeader = []
    varHeader.push((topicBytes.length >> 8) & 0xFF)
    varHeader.push(topicBytes.length & 0xFF)
    varHeader.push(...topicBytes)

    // Payload
    const payload = messageBytes

    // Remaining length
    const remainingLength = varHeader.length + payload.length
    const lengthBytes = this._encodeLength(remainingLength)

    // Fixed header (PUBLISH, QoS 0 -> 0x30)
    const packet = [0x30]
    packet.push(...lengthBytes)
    packet.push(...varHeader)
    packet.push(...payload)

    const ua = new Uint8Array(packet)
    try {
      const hex = Array.from(ua).map(b => b.toString(16).padStart(2, '0')).join(' ')
      console.log('发送 PUBLISH 包 hex:', hex)
    } catch (e) {}
    wx.sendSocketMessage({ data: ua.buffer })

    return true
  } catch (err) {
    console.error('发布失败:', err)
    return false
  }
}

SimpleMQTT.prototype.subscribe = function(topic) {
  if (!this.isConnected) {
    console.error('MQTT未连接')
    return false
  }

  try {
    const topicBytes = this._stringToBytes(topic)

    // Variable header
    const packetId = this.packetId++
    const varHeader = [(packetId >> 8) & 0xFF, packetId & 0xFF]

    // Payload
    const payload = []
    payload.push((topicBytes.length >> 8) & 0xFF)
    payload.push(topicBytes.length & 0xFF)
    payload.push(...topicBytes)
    payload.push(0) // QoS 0

    // Remaining length
    const remainingLength = varHeader.length + payload.length
    const lengthBytes = this._encodeLength(remainingLength)

    // Fixed header
    const packet = [0x82]
    packet.push(...lengthBytes)
    packet.push(...varHeader)
    packet.push(...payload)

    const ua = new Uint8Array(packet)
    try {
      const hex = Array.from(ua).map(b => b.toString(16).padStart(2, '0')).join(' ')
      console.log('发送 SUBSCRIBE 包 hex:', hex, 'topic:', topic)
    } catch (e) {}
    wx.sendSocketMessage({ data: ua.buffer })

    return true
  } catch (err) {
    console.error('订阅失败:', err)
    return false
  }
}

SimpleMQTT.prototype.onMessage = function(callback) {
  this.messageCallback = callback
}

SimpleMQTT.prototype.close = function() {
  if (this.client) {
    wx.closeSocket()
    this.isConnected = false
  }
}

SimpleMQTT.prototype._parseMessage = function(buffer) {
  if (buffer.length < 2) return

  const fixedHeader = buffer[0]
  const messageType = (fixedHeader >> 4) & 0x0F

  // 处理 CONNACK（MQTT 连接确认）
  if (messageType === 2) {
    // CONNACK 的固定结构：byte2 为连接返回码
    const ackFlags = buffer[2]
    const returnCode = buffer[3]
    console.log('收到 CONNACK:', 'ackFlags=', ackFlags, 'returnCode=', returnCode)
    this.isConnected = (returnCode === 0)
    if (this._connackResolve) {
      try { this._connackResolve() } catch (e) {}
      this._connackResolve = null
    }
    return
  }

  // 处理 SUBACK（订阅确认）
  if (messageType === 9) {
    // Packet Identifier
    const pid = (buffer[2] << 8) | buffer[3]
    const returnCodes = []
    for (let i = 4; i < buffer.length; i++) returnCodes.push(buffer[i])
    console.log('收到 SUBACK: packetId=', pid, 'returnCodes=', returnCodes)
    return
  }

  if (messageType === 3) { // PUBLISH
    let offset = 1

    // 解码 Remaining Length 并获取占用字节数
    const rlInfo = this._decodeLengthWithBytes(buffer, offset)
    const remainingLength = rlInfo.length
    offset += rlInfo.bytes

    // 标记 variable header 起始位置（用于计算 payload 长度）
    const vhStart = offset

    // Topic length
    const topicLength = (buffer[offset] << 8) | buffer[offset + 1]
    offset += 2

    // Topic
    const topic = this._bytesToString(buffer.subarray(offset, offset + topicLength))
    offset += topicLength

    // 如果 QoS > 0，则还包含 Packet Identifier（2 字节），这里简单忽略 QoS >0 的情况
    // 计算 payload 长度：remainingLength - (offset - vhStart)
    const payloadLength = remainingLength - (offset - vhStart)
    let payloadBytes = buffer.subarray(offset, offset + payloadLength)

    // 增强调试信息：打印完整包、fixedHeader、remainingLength、topic 和 payload 的 hex
    try {
      const packetHex = Array.from(buffer).map(b => b.toString(16).padStart(2, '0')).join(' ')
      console.log('完整包 hex:', packetHex)
      console.log('fixedHeader:', '0x' + fixedHeader.toString(16), 'messageType:', messageType)
      console.log('remainingLength:', remainingLength, 'vhStart:', vhStart, 'topicLength:', topicLength)
      const topicHex = Array.from(buffer.subarray(vhStart + 2, vhStart + 2 + topicLength)).map(b => b.toString(16).padStart(2, '0')).join(' ')
      console.log('topic:', topic, 'topicHex:', topicHex)
      const payloadHex = Array.from(payloadBytes).map(b => b.toString(16).padStart(2, '0')).join(' ')
      console.log('payloadHex:', payloadHex)
    } catch (e) {
      console.error('打印调试 hex 失败:', e)
    }

    // 容错：如果 payload 开头没有 '{'，尝试在 payload 中找到第一个 '{' (0x7b) 并从该处开始
    const firstBrace = payloadBytes.indexOf(0x7b)
    if (firstBrace > 0) {
      payloadBytes = payloadBytes.subarray(firstBrace)
    }

    const message = this._bytesToString(payloadBytes)

    // 尝试解析 JSON，失败时打印错误与原始字符串
    try {
      const parsed = JSON.parse(message)
      console.log('收到消息:', topic, parsed)
      if (this.messageCallback) this.messageCallback(topic, parsed)
    } catch (err) {
      console.error('JSON 解析失败:', err, 'raw:', message)
      // 将原始字符串回调，便于上层显示或调试
      if (this.messageCallback) this.messageCallback(topic, message)
    }
  }
}

// 将两个 Uint8Array 连接
SimpleMQTT.prototype._concatUint8 = function(a, b) {
  const c = new Uint8Array(a.length + b.length)
  c.set(a, 0)
  c.set(b, a.length)
  return c
}

// 尝试从缓冲区重组并处理完整的 MQTT 报文
SimpleMQTT.prototype._handleIncomingData = function(chunk) {
  // 追加到缓冲区
  this._recvBuffer = this._concatUint8(this._recvBuffer, chunk)

  // 循环解析缓冲区中的完整报文
  while (true) {
    const buf = this._recvBuffer
    if (buf.length < 2) break

    // 尝试解码 remaining length（可能需要多字节）
    const rlInfo = this._tryDecodeRemainingLength(buf, 1)
    if (!rlInfo) break // 剩余长度字段不完整，等待更多数据

    const totalLen = 1 + rlInfo.bytes + rlInfo.length
    if (buf.length < totalLen) break // 整个包未到齐

    // 取出完整包并解析
    const packet = buf.subarray(0, totalLen)
    try {
      this._parseMessage(packet)
    } catch (err) {
      console.error('解析完整包失败:', err)
    }

    // 删去已处理部分
    this._recvBuffer = buf.subarray(totalLen)
  }
}

// 尝试解码 remaining length，若字节不完整返回 null
SimpleMQTT.prototype._tryDecodeRemainingLength = function(buffer, offset) {
  let multiplier = 1
  let value = 0
  let bytes = 0
  let encodedByte = 0
  do {
    if (offset + bytes >= buffer.length) return null
    encodedByte = buffer[offset + bytes]
    value += (encodedByte & 0x7F) * multiplier
    multiplier *= 128
    bytes++
  } while ((encodedByte & 0x80) !== 0)
  return { length: value, bytes }
}

// 解码 Remaining Length，并返回长度及占用字节数
SimpleMQTT.prototype._decodeLengthWithBytes = function(buffer, offset) {
  let multiplier = 1
  let value = 0
  let bytes = 0
  let encodedByte = 0
  do {
    encodedByte = buffer[offset + bytes]
    value += (encodedByte & 0x7F) * multiplier
    multiplier *= 128
    bytes++
  } while ((encodedByte & 0x80) !== 0)
  return { length: value, bytes }
}

SimpleMQTT.prototype._encodeLength = function(length) {
  const bytes = []
  let digit = 0
  do {
    digit = length % 128
    length = Math.floor(length / 128)
    if (length > 0) {
      digit = digit | 0x80
    }
    bytes.push(digit)
  } while (length > 0)
  return bytes
}

SimpleMQTT.prototype._decodeLength = function(buffer, offset) {
  let multiplier = 1
  let length = 0
  let encodedByte = 0

  do {
    encodedByte = buffer[offset++]
    length += (encodedByte & 0x7F) * multiplier
    multiplier *= 128
  } while ((encodedByte & 0x80) !== 0)

  return length
}

SimpleMQTT.prototype._getLengthBytes = function(length) {
  let count = 0
  do {
    length = length >> 7
    count++
  } while (length > 0)
  return count
}

SimpleMQTT.prototype._stringToBytes = function(str) {
  const bytes = []
  for (let i = 0; i < str.length; i++) {
    bytes.push(str.charCodeAt(i))
  }
  return bytes
}

SimpleMQTT.prototype._bytesToString = function(bytes) {
  let str = ''
  for (let i = 0; i < bytes.length; i++) {
    str += String.fromCharCode(bytes[i])
  }
  return str
}

SimpleMQTT.prototype._bufferToBase64 = function(buffer) {
  // 接受 ArrayBuffer 或 Uint8Array
  let ab
  if (buffer instanceof ArrayBuffer) ab = buffer
  else if (buffer && buffer.buffer instanceof ArrayBuffer) ab = buffer.buffer
  else ab = new Uint8Array(buffer).buffer
  return wx.arrayBufferToBase64(ab)
}

SimpleMQTT.prototype._base64ToArrayBuffer = function(base64) {
  const binary = wx.base64ToArrayBuffer(base64)
  return binary
}

module.exports = SimpleMQTT
