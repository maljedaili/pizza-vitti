# Camera gateway setup

This setup is installed once in every restaurant, shop, office, or project.

## Architecture

The Django dashboard does not receive or record camera video. The owner device connects directly to a private gateway at each location:

`Camera/NVR -> go2rtc gateway -> Tailscale private network -> owner browser`

Camera RTSP usernames and passwords remain in `camera-gateway/go2rtc.yaml` on the local gateway. They must never be entered in the Pizza Vitti dashboard or committed to Git.

## Requirements per location

- One Linux mini PC, Raspberry Pi 4/5, or compatible NVR.
- Ethernet connection recommended.
- Local IP address and RTSP path for every camera.
- Cameras with H.264 video for broad browser compatibility.
- A speaker and supported backchannel protocol for two-way audio.
- Tailscale on the gateway and every owner phone, tablet, or computer.

ONVIF Profile T includes bidirectional audio, but support still depends on the exact camera model, firmware, codec, and gateway configuration.

## Install Docker and go2rtc

Copy the example files:

```bash
mkdir -p camera-gateway
cd camera-gateway
cp docker-compose.yml.example docker-compose.yml
cp go2rtc.yaml.example go2rtc.yaml
```

Edit only the local `go2rtc.yaml` with the real camera addresses and credentials. Test locally:

```bash
docker compose up -d
docker compose logs -f go2rtc
```

The go2rtc API listens only on `127.0.0.1:1984`. WebRTC media listens on TCP/UDP `8555`.

## Private HTTPS access

Install Tailscale and authenticate the gateway:

```bash
sudo tailscale up
sudo tailscale serve --bg 1984
tailscale serve status
```

Tailscale returns a private HTTPS URL similar to:

```text
https://camera-bordeaux.example-tailnet.ts.net
```

Add this HTTPS URL to the owner dashboard as the location gateway. Add the exact stream names from `go2rtc.yaml` as cameras.

The tailnet access policy should permit only owner devices/users to reach gateway TCP `443` and WebRTC TCP/UDP `8555`.

Example Tailscale grants template:

```json
{
  "groups": {
    "group:camera-owners": ["OWNER_EMAIL_ADDRESS"]
  },
  "tagOwners": {
    "tag:camera-gateway": ["autogroup:admin"]
  },
  "grants": [
    {
      "src": ["group:camera-owners"],
      "dst": ["tag:camera-gateway"],
      "ip": ["tcp:443", "tcp:8555", "udp:8555"]
    }
  ]
}
```

Keep any existing tailnet policy entries when adding this grant, then assign the tag on every location gateway:

```bash
sudo tailscale up --advertise-tags=tag:camera-gateway
```

## Two-way audio

Before enabling "Parler via le micro":

1. Confirm the camera has a physical speaker.
2. Confirm the exact model supports ONVIF Profile T or another go2rtc two-way audio source.
3. Open the go2rtc links page and test WebRTC with `video+audio+microphone`.
4. If the camera uses AAC audio, an FFmpeg OPUS source may be required for browser compatibility.
5. Test from the owner's phone while it is outside the restaurant Wi-Fi.

The browser requires HTTPS and explicit microphone permission. The dashboard cannot add talk capability to a camera that lacks a supported audio backchannel.

## Security checklist

- Do not expose go2rtc with Tailscale Funnel or an open router port.
- Do not put RTSP credentials in dashboard URLs.
- Do not commit the real `go2rtc.yaml`.
- Restrict Tailscale access to the owner and approved devices.
- Keep cameras, gateway OS, Docker, go2rtc, and Tailscale updated.
- Use separate camera accounts with only the permissions required.
- Verify local legal requirements, staff information, signage, retention, and audio-recording rules before enabling surveillance.
