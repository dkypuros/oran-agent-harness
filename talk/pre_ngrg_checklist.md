---
title: "Pre-nGRG morning-of checklist"
author: David Kypuros
venue: O-RAN nGRG Workshop, Seattle
date: 4th [THU] JUN 2026
license: Apache-2.0
status: operational checklist David runs the morning of the talk
---

# Pre-nGRG Checklist

Run this list the morning of 4 June 2026 before walking into the venue. Each item has a
specific verification step. Do not skip; this list exists because the cost of any single item
failing live is much higher than the cost of checking it 30 minutes before.

## T-90 minutes (90 minutes before talk start)

  - [ ] **Laptop battery at 100 percent.** Both the demo laptop and the backup.
  - [ ] **MacBook lab cold start.** Run `cd macbook_lab && ./run.sh` from a fresh terminal.
        Verify the 7 services come up (8 with `--profile dashboard`).
  - [ ] **Health endpoints all green.** Run all 8 curl checks:
        ```
        curl -sf http://localhost:8090/                           # fake-vllm
        curl -sf http://localhost:8091/health                     # ptp-operator
        curl -sf http://localhost:8092/health                     # metal3-bmo
        curl -sf http://localhost:8093/health                     # redfish-bmc
        curl -sf http://localhost:8094/health                     # tmf921-smo
        curl -sf http://localhost:8095/dashboard/trace_view/      # trace viewer
        curl -sf http://localhost:8096/health                     # harness-walker
        curl -sf http://localhost:8097                            # dashboard
        ```
        Every one should return non-error within 60 seconds. If any fail, fix or pivot to the
        recorded demo (see Fallbacks below).
  - [ ] **Run the canonical scenario walk.**
        `curl -s http://localhost:8096/run/E_nic_firmware_update | jq .`
        Confirm `companion_intent_attached: true` in the response. Confirm the trace JSONL
        file at `5G_O-RAN_SIM/shared_trace/E_nic_firmware_update.jsonl` has at least 10 lines.
  - [ ] **Recorded demo loaded.** Open the canonical recording in QuickTime (or whichever
        player) on the demo laptop. Verify it plays through end-to-end with no missing audio
        or video. The recording is the fallback if the live lab fails on stage.
  - [ ] **Slide deck synced.** Open the slide deck on the demo laptop. Click through every
        slide to verify embedded images render. Confirm the slide order matches
        `talk/runsheet_25min.md`.

## T-60 minutes

  - [ ] **Backup USB stick prepared.** Copy onto a labeled USB:
        - The recorded demo (the same file as on the laptop)
        - The slide deck PDF export (in case the native format fails to open on the venue
          projector)
        - The static trace viewer (`5G_O-RAN_SIM/dashboard/trace_view/index.html`) and its
          assets, openable from local disk if the lab is unreachable
        - `talk/runsheet_25min.md` printed to PDF as a backup speaking aid
  - [ ] **Repo URL on a card.** Print or write `github.com/dkypuros/oran-agent-harness` on
        an index card. Stick it in your pocket. Anyone who asks for the slides gets the URL
        instead.
  - [ ] **Network check.** Test the venue WiFi with `curl -sf https://api.anthropic.com`
        if the talk uses LLM live mode, OR confirm `ORAN_LLM_MODE` is unset (default fake
        vLLM mock) if the talk does not need a live call.
  - [ ] **Phone charged and on silent.** No notifications during the talk.

## T-30 minutes

  - [ ] **Walk into the venue.** Find the AV technician. Confirm the projector connector
        matches your laptop (USB-C, HDMI, or whatever the venue has). If not, the venue
        usually has an adapter; ask now.
  - [ ] **Projector test.** Mirror your screen to the projector. Open the slide deck. Confirm
        it renders correctly (resolution, aspect ratio, color). Open the recorded demo and
        confirm video and audio play through the venue PA.
  - [ ] **Microphone test.** If a lapel mic is provided, clip it on, ask the AV tech to test
        levels. If not, confirm the podium mic is on and within reach.
  - [ ] **Backup laptop ready.** If the primary laptop fails, the backup boots and shows the
        same slides plus the recorded demo. Walk through the boot in the venue if you have
        time.

## T-5 minutes

  - [ ] **Water bottle.** Within reach.
  - [ ] **Slide 1 displayed on the projector.** Title slide, repo URL visible.
  - [ ] **Runsheet open on the laptop.** `talk/runsheet_25min.md` open in a second window so
        you can glance at it during transitions.
  - [ ] **Lab status one final check.** `curl -sf http://localhost:8096/health` returns 200.
        If yes, the live demo option is in play. If no, switch mentally to the recorded
        demo for slide 6 without panic.
  - [ ] **Phone goes face-down.**

## During the talk

You should not need this file during the talk. The runsheet at `talk/runsheet_25min.md` is the
operational artifact for that. But if something fails:

  - **The lab freezes mid-demo.** Switch to the recorded demo. Say "the recording covers the
    same walk." Do not narrate the failure; the audience does not care.
  - **The projector loses sync.** Pause for 10 seconds. Ask the AV tech with one hand
    gesture. Continue speaking from memory while they restore the signal. The audience knows
    AV failures are not the speaker's fault.
  - **A microphone dies.** Switch to the backup mic if available. If not, project from the
    diaphragm and keep going. Apologize once, briefly. Move on.
  - **A question outside scope.** "Good question. The repo has an entry on that under
    `talk/reviewer_faq.md`. Happy to walk it at the break." Move on.

## After the talk

  - [ ] **Take questions for the full Q&A window.** Do not exit the stage early.
  - [ ] **Stay in the room for 10 minutes after.** Coffee-break ambushes happen here.
        Use `talk/pitch_5min.md` for these conversations.
  - [ ] **Note audience reactions.** Mental notes for the post-talk log. Specific names with
        opinions stay private; aggregate reactions go in the post-nGRG handoff materials.
  - [ ] **Post to Twitter / X within 60 minutes.** Use the template in
        `talk/post_ngrg_handoff.md`.
  - [ ] **Post to LinkedIn same evening.** Different template, same handoff file.

## Fallbacks summary

| If this fails           | Fallback                                                      |
|-------------------------|---------------------------------------------------------------|
| MacBook lab live demo   | Recorded demo (loaded on laptop and USB)                      |
| Recorded demo file      | oh-my-tiny-oran chat live at `:8097/#chat` (Path 3 in slide 6); falls back further to trace viewer at `:8095` |
| oh-my-tiny-oran chat    | Trace timeline viewer at `:8095/dashboard/trace_view/index.html` (deterministic, no LLM, no internet) |
| Slide deck native open  | PDF export from USB                                           |
| Primary laptop          | Backup laptop, USB has everything needed                      |
| Network connectivity    | Recorded demo + slides only, no live LLM, no live curl, oh-my-tiny-oran unavailable |
| Projector connector     | Venue adapter (ask AV tech at T-30)                           |
| Mermaid diagram render  | PNG export already committed alongside every `.mmd` in talk/  |
| Forgotten slide content | Runsheet open in second window                                |
| Question outside scope  | Point at `talk/reviewer_faq.md`, defer to coffee break        |

The talk is engineered to land even if every live element fails. The recording is the
foundation; everything else is enhancement.

## One last thing

You have done the work. The bench is verified, the narrative is anchored, the runsheet is
written. The talk is 25 minutes; the bench is durable. Whatever happens on stage is one
moment.

Go give it.
