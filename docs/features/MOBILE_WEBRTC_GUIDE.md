# Mobile WebRTC Connection Guide for Conversational AI

Complete guide for establishing WebRTC connections from mobile apps (iOS/Android/React Native) to the Conversational AI server.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Server Configuration](#server-configuration)
4. [Connection Flow](#connection-flow)
5. [iOS Implementation](#ios-implementation)
6. [Android Implementation](#android-implementation)
7. [React Native Implementation](#react-native-implementation)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The conversational AI uses WebRTC for real-time bidirectional audio streaming between the mobile client and the AI assistant. The connection requires:

- **Firebase ID Token** or **IoT Session Token** for authentication
- **WebRTC peer connection** with proper ICE server configuration
- **Microphone permissions** for audio input
- **Audio playback** for receiving AI responses

### Architecture

```
Mobile App → WebRTC Offer → Server
          ← WebRTC Answer ←
          ↔ ICE Candidates ↔
          ↔ Audio Streams  ↔
```

---

## Prerequisites

### Required Information

1. **Server URL**: `https://your-server-domain.com` (or `http://localhost:8000` for local testing)
2. **Authentication Token**: Firebase ID token or IoT session token
3. **Story ID** (optional): For story-specific conversations

### Required Permissions

**iOS (Info.plist)**:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>We need microphone access for voice conversations with the AI storyteller</string>
```

**Android (AndroidManifest.xml)**:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

---

## Server Configuration

The server is configured to work behind NAT/firewalls with the following ICE servers:

### STUN Servers
```javascript
{ urls: 'stun:stun.l.google.com:19302' }
{ urls: 'stun:stun1.l.google.com:19302' }
```

### TURN Servers (for NAT traversal)
```javascript
{
  urls: 'turn:global.turn.twilio.com:3478?transport=udp',
  username: 'f4b4035eaa76f4a55de5f4351567653ee4ff6fa97b50b6b334fcc1be9c27212d',
  credential: 'w1uxM55V9yVoqyVFjt+mxDBV0F87AUCemaYVQGxsPLw='
}
```

**Server Public IP**: `34.60.150.7` (Google Cloud VM)

---

## Connection Flow

### Step-by-Step Process

```
1. Initialize RTCPeerConnection with ICE servers
   ↓
2. Request microphone permissions
   ↓
3. Add local audio track to peer connection
   ↓
4. Create WebRTC offer
   ↓
5. Send offer to server (POST /conversation/api/offer)
   ↓
6. Receive WebRTC answer from server
   ↓
7. Set remote description
   ↓
8. Exchange ICE candidates (PATCH /conversation/api/offer)
   ↓
9. Connection established
   ↓
10. Start receiving AI audio responses
```

### API Endpoints

#### 1. Create Connection (Send Offer)

**Endpoint**: `POST /conversation/api/offer`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN_HERE
```

**Request Body**:
```json
{
  "session_token": "YOUR_FIREBASE_OR_IOT_TOKEN",
  "story_id": "optional-story-id",
  "sdp": "v=0\r\no=- ...",
  "type": "offer"
}
```

**Response**:
```json
{
  "pc_id": "unique-connection-id",
  "sdp": "v=0\r\no=- ...",
  "type": "answer"
}
```

#### 2. Send ICE Candidates

**Endpoint**: `PATCH /conversation/api/offer`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN_HERE
```

**Request Body**:
```json
{
  "pc_id": "unique-connection-id",
  "ice_candidate": {
    "candidate": "candidate:... ",
    "sdpMid": "0",
    "sdpMLineIndex": 0
  }
}
```

---

## iOS Implementation

### Using WebRTC Framework

```swift
import WebRTC

class ConversationManager: NSObject {
    private var peerConnection: RTCPeerConnection?
    private var pcId: String?
    private let serverUrl = "https://your-server-domain.com"
    private var authToken: String
    
    // MARK: - Configuration
    
    func createPeerConnection() {
        // Configure ICE servers
        let config = RTCConfiguration()
        config.iceServers = [
            RTCIceServer(urlStrings: ["stun:stun.l.google.com:19302"]),
            RTCIceServer(urlStrings: ["stun:stun1.l.google.com:19302"]),
            RTCIceServer(
                urlStrings: ["turn:global.turn.twilio.com:3478?transport=udp"],
                username: "f4b4035eaa76f4a55de5f4351567653ee4ff6fa97b50b6b334fcc1be9c27212d",
                credential: "w1uxM55V9yVoqyVFjt+mxDBV0F87AUCemaYVQGxsPLw="
            )
        ]
        
        // Optional: Force TURN relay (uncomment for testing)
        // config.iceTransportPolicy = .relay
        
        // Create constraints
        let constraints = RTCMediaConstraints(
            mandatoryConstraints: nil,
            optionalConstraints: nil
        )
        
        // Create peer connection
        let factory = RTCPeerConnectionFactory()
        peerConnection = factory.peerConnection(
            with: config,
            constraints: constraints,
            delegate: self
        )
    }
    
    // MARK: - Local Audio Setup
    
    func setupLocalAudio() {
        guard let peerConnection = peerConnection else { return }
        
        // Create audio track
        let factory = RTCPeerConnectionFactory()
        let audioConstraints = RTCMediaConstraints(
            mandatoryConstraints: [
                "googEchoCancellation": "true",
                "googAutoGainControl": "true",
                "googNoiseSuppression": "true"
            ],
            optionalConstraints: nil
        )
        
        let audioSource = factory.audioSource(with: audioConstraints)
        let audioTrack = factory.audioTrack(with: audioSource, trackId: "audio0")
        
        // Add track to peer connection
        peerConnection.add(audioTrack, streamIds: ["stream0"])
        
        print("✅ Local audio track added")
    }
    
    // MARK: - Create and Send Offer
    
    func connect(storyId: String? = nil) {
        setupLocalAudio()
        
        // Create offer
        let constraints = RTCMediaConstraints(
            mandatoryConstraints: [
                "OfferToReceiveAudio": "true",
                "OfferToReceiveVideo": "false"
            ],
            optionalConstraints: nil
        )
        
        peerConnection?.offer(for: constraints) { [weak self] sdp, error in
            guard let self = self, let sdp = sdp, error == nil else {
                print("❌ Failed to create offer: \(error?.localizedDescription ?? "unknown")")
                return
            }
            
            // Set local description
            self.peerConnection?.setLocalDescription(sdp) { error in
                if let error = error {
                    print("❌ Failed to set local description: \(error.localizedDescription)")
                    return
                }
                
                // Send offer to server
                self.sendOffer(sdp: sdp, storyId: storyId)
            }
        }
    }
    
    private func sendOffer(sdp: RTCSessionDescription, storyId: String?) {
        let url = URL(string: "\(serverUrl)/conversation/api/offer")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        
        let body: [String: Any] = [
            "session_token": authToken,
            "story_id": storyId as Any,
            "sdp": sdp.sdp,
            "type": sdp.type.rawValue
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self,
                  let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let answerSdp = json["sdp"] as? String,
                  let answerType = json["type"] as? String,
                  let pcId = json["pc_id"] as? String else {
                print("❌ Failed to parse server response")
                return
            }
            
            self.pcId = pcId
            print("✅ Received answer from server (pc_id: \(pcId))")
            
            // Set remote description
            let answer = RTCSessionDescription(
                type: answerType == "answer" ? .answer : .offer,
                sdp: answerSdp
            )
            
            self.peerConnection?.setRemoteDescription(answer) { error in
                if let error = error {
                    print("❌ Failed to set remote description: \(error.localizedDescription)")
                } else {
                    print("✅ Remote description set - connection established!")
                }
            }
        }.resume()
    }
    
    // MARK: - ICE Candidate Handling
    
    private func sendIceCandidate(_ candidate: RTCIceCandidate) {
        guard let pcId = pcId else { return }
        
        let url = URL(string: "\(serverUrl)/conversation/api/offer")!
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        
        let body: [String: Any] = [
            "pc_id": pcId,
            "ice_candidate": [
                "candidate": candidate.sdp,
                "sdpMid": candidate.sdpMid ?? "",
                "sdpMLineIndex": candidate.sdpMLineIndex
            ]
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request).resume()
    }
}

// MARK: - RTCPeerConnectionDelegate

extension ConversationManager: RTCPeerConnectionDelegate {
    func peerConnection(_ peerConnection: RTCPeerConnection, didChange state: RTCSignalingState) {
        print("📡 Signaling state: \(state.rawValue)")
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didAdd stream: RTCMediaStream) {
        print("✅ Received remote stream with \(stream.audioTracks.count) audio tracks")
        
        // Play remote audio
        if let audioTrack = stream.audioTracks.first {
            audioTrack.source.volume = 1.0
            print("🔊 Playing remote audio")
        }
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didRemove stream: RTCMediaStream) {
        print("⚠️ Remote stream removed")
    }
    
    func peerConnectionShouldNegotiate(_ peerConnection: RTCPeerConnection) {
        print("🔄 Negotiation needed")
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didChange newState: RTCIceConnectionState) {
        print("🧊 ICE connection state: \(newState.rawValue)")
        
        switch newState {
        case .connected, .completed:
            print("✅ ICE connection established!")
        case .failed:
            print("❌ ICE connection failed!")
        case .disconnected:
            print("⚠️ ICE disconnected")
        default:
            break
        }
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didChange newState: RTCIceGatheringState) {
        print("🧊 ICE gathering state: \(newState.rawValue)")
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didGenerate candidate: RTCIceCandidate) {
        print("🧊 Generated ICE candidate: \(candidate.sdp)")
        sendIceCandidate(candidate)
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didRemove candidates: [RTCIceCandidate]) {
        print("⚠️ ICE candidates removed")
    }
    
    func peerConnection(_ peerConnection: RTCPeerConnection, didOpen dataChannel: RTCDataChannel) {
        print("📦 Data channel opened")
    }
}
```

---

## Android Implementation

### Using WebRTC Library

```kotlin
import org.webrtc.*
import kotlinx.coroutines.*
import okhttp3.*
import org.json.JSONObject

class ConversationManager(private val authToken: String) {
    private var peerConnection: PeerConnection? = null
    private var pcId: String? = null
    private val serverUrl = "https://your-server-domain.com"
    private val scope = CoroutineScope(Dispatchers.Main)
    
    // MARK: - Configuration
    
    fun createPeerConnection(context: Context) {
        // Initialize WebRTC
        val options = PeerConnectionFactory.InitializationOptions.builder(context)
            .setEnableInternalTracer(true)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(options)
        
        // Create peer connection factory
        val factory = PeerConnectionFactory.builder().createPeerConnectionFactory()
        
        // Configure ICE servers
        val iceServers = listOf(
            PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer(),
            PeerConnection.IceServer.builder("stun:stun1.l.google.com:19302").createIceServer(),
            PeerConnection.IceServer.builder("turn:global.turn.twilio.com:3478?transport=udp")
                .setUsername("f4b4035eaa76f4a55de5f4351567653ee4ff6fa97b50b6b334fcc1be9c27212d")
                .setPassword("w1uxM55V9yVoqyVFjt+mxDBV0F87AUCemaYVQGxsPLw=")
                .createIceServer()
        )
        
        val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply {
            // Optional: Force TURN relay (uncomment for testing)
            // iceTransportsType = PeerConnection.IceTransportsType.RELAY
        }
        
        // Create peer connection
        peerConnection = factory.createPeerConnection(rtcConfig, object : PeerConnection.Observer {
            override fun onIceCandidate(candidate: IceCandidate) {
                sendIceCandidate(candidate)
            }
            
            override fun onAddStream(stream: MediaStream) {
                println("✅ Received remote stream with ${stream.audioTracks.size} audio tracks")
                if (stream.audioTracks.isNotEmpty()) {
                    val audioTrack = stream.audioTracks[0]
                    audioTrack.setEnabled(true)
                    println("🔊 Playing remote audio")
                }
            }
            
            override fun onIceConnectionChange(state: PeerConnection.IceConnectionState) {
                println("🧊 ICE connection state: $state")
                when (state) {
                    PeerConnection.IceConnectionState.CONNECTED,
                    PeerConnection.IceConnectionState.COMPLETED -> {
                        println("✅ ICE connection established!")
                    }
                    PeerConnection.IceConnectionState.FAILED -> {
                        println("❌ ICE connection failed!")
                    }
                    else -> {}
                }
            }
            
            override fun onSignalingChange(state: PeerConnection.SignalingState) {
                println("📡 Signaling state: $state")
            }
            
            override fun onIceGatheringChange(state: PeerConnection.IceGatheringState) {
                println("🧊 ICE gathering state: $state")
            }
            
            // Other required overrides...
            override fun onRemoveStream(stream: MediaStream) {}
            override fun onDataChannel(channel: DataChannel) {}
            override fun onRenegotiationNeeded() {}
            override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>) {}
        })
        
        // Setup local audio
        setupLocalAudio(factory)
    }
    
    // MARK: - Local Audio Setup
    
    private fun setupLocalAudio(factory: PeerConnectionFactory) {
        // Create audio source
        val audioConstraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("googEchoCancellation", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("googAutoGainControl", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("googNoiseSuppression", "true"))
        }
        
        val audioSource = factory.createAudioSource(audioConstraints)
        val audioTrack = factory.createAudioTrack("audio0", audioSource)
        
        // Add track to peer connection
        peerConnection?.addTrack(audioTrack, listOf("stream0"))
        
        println("✅ Local audio track added")
    }
    
    // MARK: - Create and Send Offer
    
    fun connect(storyId: String? = null) {
        val constraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
        }
        
        peerConnection?.createOffer(object : SdpObserver {
            override fun onCreateSuccess(sdp: SessionDescription) {
                peerConnection?.setLocalDescription(object : SdpObserver {
                    override fun onSetSuccess() {
                        sendOffer(sdp, storyId)
                    }
                    
                    override fun onSetFailure(error: String) {
                        println("❌ Failed to set local description: $error")
                    }
                    
                    override fun onCreateSuccess(p0: SessionDescription?) {}
                    override fun onCreateFailure(p0: String?) {}
                }, sdp)
            }
            
            override fun onCreateFailure(error: String) {
                println("❌ Failed to create offer: $error")
            }
            
            override fun onSetSuccess() {}
            override fun onSetFailure(p0: String?) {}
        }, constraints)
    }
    
    private fun sendOffer(sdp: SessionDescription, storyId: String?) {
        scope.launch(Dispatchers.IO) {
            val client = OkHttpClient()
            val json = JSONObject().apply {
                put("session_token", authToken)
                put("story_id", storyId)
                put("sdp", sdp.description)
                put("type", sdp.type.canonicalForm())
            }
            
            val request = Request.Builder()
                .url("$serverUrl/conversation/api/offer")
                .post(RequestBody.create(MediaType.parse("application/json"), json.toString()))
                .addHeader("Authorization", "Bearer $authToken")
                .build()
            
            try {
                val response = client.newCall(request).execute()
                val responseBody = JSONObject(response.body()?.string() ?: "")
                
                pcId = responseBody.getString("pc_id")
                val answerSdp = responseBody.getString("sdp")
                val answerType = responseBody.getString("type")
                
                println("✅ Received answer from server (pc_id: $pcId)")
                
                withContext(Dispatchers.Main) {
                    val answer = SessionDescription(
                        SessionDescription.Type.fromCanonicalForm(answerType),
                        answerSdp
                    )
                    
                    peerConnection?.setRemoteDescription(object : SdpObserver {
                        override fun onSetSuccess() {
                            println("✅ Remote description set - connection established!")
                        }
                        
                        override fun onSetFailure(error: String) {
                            println("❌ Failed to set remote description: $error")
                        }
                        
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onCreateFailure(p0: String?) {}
                    }, answer)
                }
            } catch (e: Exception) {
                println("❌ Failed to send offer: ${e.message}")
            }
        }
    }
    
    // MARK: - ICE Candidate Handling
    
    private fun sendIceCandidate(candidate: IceCandidate) {
        val currentPcId = pcId ?: return
        
        scope.launch(Dispatchers.IO) {
            val client = OkHttpClient()
            val json = JSONObject().apply {
                put("pc_id", currentPcId)
                put("ice_candidate", JSONObject().apply {
                    put("candidate", candidate.sdp)
                    put("sdpMid", candidate.sdpMid)
                    put("sdpMLineIndex", candidate.sdpMLineIndex)
                })
            }
            
            val request = Request.Builder()
                .url("$serverUrl/conversation/api/offer")
                .patch(RequestBody.create(MediaType.parse("application/json"), json.toString()))
                .addHeader("Authorization", "Bearer $authToken")
                .build()
            
            client.newCall(request).execute()
        }
    }
}
```

---

## React Native Implementation

### Using react-native-webrtc

```typescript
import {
  RTCPeerConnection,
  RTCIceCandidate,
  RTCSessionDescription,
  mediaDevices,
  MediaStream,
} from 'react-native-webrtc';

class ConversationManager {
  private peerConnection: RTCPeerConnection | null = null;
  private pcId: string | null = null;
  private serverUrl = 'https://your-server-domain.com';
  private authToken: string;
  
  constructor(authToken: string) {
    this.authToken = authToken;
  }
  
  // MARK: - Configuration
  
  async createPeerConnection() {
    // Configure ICE servers
    const configuration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        {
          urls: 'turn:global.turn.twilio.com:3478?transport=udp',
          username: 'f4b4035eaa76f4a55de5f4351567653ee4ff6fa97b50b6b334fcc1be9c27212d',
          credential: 'w1uxM55V9yVoqyVFjt+mxDBV0F87AUCemaYVQGxsPLw=',
        },
      ],
      // Optional: Force TURN relay (uncomment for testing)
      // iceTransportPolicy: 'relay',
    };
    
    // Create peer connection
    this.peerConnection = new RTCPeerConnection(configuration);
    
    // Setup event handlers
    this.setupEventHandlers();
    
    // Setup local audio
    await this.setupLocalAudio();
  }
  
  // MARK: - Event Handlers
  
  private setupEventHandlers() {
    if (!this.peerConnection) return;
    
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('🧊 Generated ICE candidate');
        this.sendIceCandidate(event.candidate);
      }
    };
    
    this.peerConnection.ontrack = (event) => {
      console.log('✅ Received remote track:', event.track.kind);
      if (event.streams && event.streams[0]) {
        console.log('🔊 Playing remote audio stream');
        // The audio will play automatically on the device speaker
      }
    };
    
    this.peerConnection.onconnectionstatechange = () => {
      console.log('📡 Connection state:', this.peerConnection?.connectionState);
      
      if (this.peerConnection?.connectionState === 'connected') {
        console.log('✅ WebRTC connection established!');
      } else if (
        this.peerConnection?.connectionState === 'failed' ||
        this.peerConnection?.connectionState === 'disconnected'
      ) {
        console.log('❌ Connection failed or disconnected');
      }
    };
    
    this.peerConnection.oniceconnectionstatechange = () => {
      console.log('🧊 ICE connection state:', this.peerConnection?.iceConnectionState);
    };
  }
  
  // MARK: - Local Audio Setup
  
  private async setupLocalAudio() {
    try {
      // Request microphone access
      const stream = await mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      
      console.log('✅ Microphone access granted');
      
      // Add audio tracks to peer connection
      stream.getTracks().forEach((track) => {
        this.peerConnection?.addTrack(track, stream);
        console.log('✅ Added local track:', track.kind);
      });
    } catch (error) {
      console.error('❌ Failed to get microphone access:', error);
      throw error;
    }
  }
  
  // MARK: - Create and Send Offer
  
  async connect(storyId?: string) {
    if (!this.peerConnection) {
      await this.createPeerConnection();
    }
    
    try {
      // Create offer
      console.log('Creating WebRTC offer...');
      const offer = await this.peerConnection!.createOffer({
        offerToReceiveAudio: true,
        offerToReceiveVideo: false,
      });
      
      // Set local description
      await this.peerConnection!.setLocalDescription(offer);
      console.log('✅ Local description set');
      
      // Send offer to server
      await this.sendOffer(offer, storyId);
    } catch (error) {
      console.error('❌ Failed to create or send offer:', error);
      throw error;
    }
  }
  
  private async sendOffer(offer: RTCSessionDescription, storyId?: string) {
    try {
      const response = await fetch(`${this.serverUrl}/conversation/api/offer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authToken}`,
        },
        body: JSON.stringify({
          session_token: this.authToken,
          story_id: storyId,
          sdp: offer.sdp,
          type: offer.type,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.statusText}`);
      }
      
      const data = await response.json();
      this.pcId = data.pc_id;
      console.log('✅ Received answer from server (pc_id:', this.pcId, ')');
      
      // Set remote description
      const answer = new RTCSessionDescription({
        type: data.type,
        sdp: data.sdp,
      });
      
      await this.peerConnection!.setRemoteDescription(answer);
      console.log('✅ Remote description set - connection established!');
    } catch (error) {
      console.error('❌ Failed to send offer:', error);
      throw error;
    }
  }
  
  // MARK: - ICE Candidate Handling
  
  private async sendIceCandidate(candidate: RTCIceCandidate) {
    if (!this.pcId) return;
    
    try {
      await fetch(`${this.serverUrl}/conversation/api/offer`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.authToken}`,
        },
        body: JSON.stringify({
          pc_id: this.pcId,
          ice_candidate: {
            candidate: candidate.candidate,
            sdpMid: candidate.sdpMid,
            sdpMLineIndex: candidate.sdpMLineIndex,
          },
        }),
      });
      
      console.log('✅ ICE candidate sent');
    } catch (error) {
      console.error('❌ Failed to send ICE candidate:', error);
    }
  }
  
  // MARK: - Disconnect
  
  disconnect() {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
      this.pcId = null;
      console.log('✅ Disconnected');
    }
  }
}

// Usage example
const manager = new ConversationManager(firebaseToken);
await manager.connect(storyId);
```

---

## Troubleshooting

### Common Issues

#### 1. "ICE Connection Failed"

**Problem**: ICE candidates cannot establish connection

**Solutions**:
- ✅ Verify TURN servers are configured correctly
- ✅ Check if firewall is blocking UDP ports
- ✅ Try forcing TURN relay: `iceTransportPolicy: 'relay'`
- ✅ Ensure server public IP (34.60.150.7) is accessible

#### 2. "No Audio Received"

**Problem**: Connection established but no audio from AI

**Solutions**:
- ✅ Check microphone permissions are granted
- ✅ Verify audio track is added to peer connection
- ✅ Check browser/app autoplay policy (may require user interaction)
- ✅ Verify remote track is received in `ontrack` event
- ✅ Check audio element/player is not muted

#### 3. "Authentication Failed"

**Problem**: Token rejected by server

**Solutions**:
- ✅ Verify Firebase token is valid and not expired
- ✅ Check token is sent in Authorization header: `Bearer YOUR_TOKEN`
- ✅ For IoT devices, ensure session token is generated correctly

#### 4. "Connection Timeout"

**Problem**: Offer sent but no answer received

**Solutions**:
- ✅ Server may be initializing models (first request takes 10-15 seconds)
- ✅ Increase timeout to 30+ seconds
- ✅ Check server logs for errors
- ✅ Verify network connectivity

#### 5. "Private IP in Candidates"

**Problem**: Server sending private IP (10.128.0.3) instead of public IP

**Solutions**:
- ✅ Server is configured with TURN servers for NAT traversal
- ✅ TURN relay will handle traffic when direct connection fails
- ✅ Client should try all candidates (host, srflx, relay)
- ✅ Force relay mode for testing: `iceTransportPolicy: 'relay'`

### Debug Logging

Enable verbose logging to diagnose issues:

```javascript
// Log all ICE candidates
pc.onicecandidate = (event) => {
  if (event.candidate) {
    console.log('ICE Candidate:', {
      type: event.candidate.type,
      protocol: event.candidate.protocol,
      address: event.candidate.address,
      port: event.candidate.port,
      candidate: event.candidate.candidate
    });
  }
};

// Log connection states
pc.oniceconnectionstatechange = () => {
  console.log('ICE State:', pc.iceConnectionState);
};

pc.onconnectionstatechange = () => {
  console.log('Connection State:', pc.connectionState);
};

// Log tracks
pc.ontrack = (event) => {
  console.log('Track:', {
    kind: event.track.kind,
    enabled: event.track.enabled,
    muted: event.track.muted,
    readyState: event.track.readyState
  });
};
```

### Network Requirements

**Ports that must be open:**
- TCP 443 (HTTPS)
- TCP 3478 (TURN)
- UDP 3478 (TURN)
- UDP 49152-65535 (WebRTC media)

**Firewall Rules:**
- Allow outbound connections to server IP: 34.60.150.7
- Allow outbound connections to TURN servers: global.turn.twilio.com
- Allow outbound UDP for WebRTC media

---

## Testing Checklist

Before deploying to production, test:

- [ ] Connection establishes successfully
- [ ] Audio from device is received by server
- [ ] Audio from server plays on device
- [ ] Connection survives network switches (WiFi ↔ Cellular)
- [ ] Connection recovers from temporary disconnections
- [ ] Multiple concurrent connections work
- [ ] Connection works behind corporate firewall
- [ ] Connection works on mobile data (not just WiFi)
- [ ] Audio quality is acceptable
- [ ] Latency is under 500ms

---

## Support

For issues or questions:
1. Check server logs for errors
2. Enable verbose WebRTC logging
3. Test with web client first (test-conversation.html)
4. Verify authentication token is valid
5. Check network connectivity and firewall rules

## Server Configuration Summary

- **Public IP**: 34.60.150.7
- **Internal IP**: 10.128.0.3
- **STUN Servers**: Google STUN servers
- **TURN Servers**: Twilio global TURN
- **WebRTC Library**: aiortc (Python)
- **Framework**: Pipecat with SmallWebRTC transport
