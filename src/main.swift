import Cocoa
import WebKit
import Carbon.HIToolbox   // global push-to-talk hotkey (no Accessibility needed)

// J.A.R.V.I.S. — kilit açılışında çalışan sinematik HUD ajanı.
// - Ekran kilidi açıldığında (com.apple.screenIsUnlocked) tetiklenir.
// - Her ekrana kenarlıksız, saydam, tıklama geçirgen bir overlay açar.
// - Bundle içindeki index.html HUD'ını WKWebView ile gösterir.
// - "say -v Daniel" ile İngiliz aksanlı karşılama yapar.
// - ~6 saniye sonra yumuşakça solup kapanır.

let GREETING = "Welcome back, Doctor. All systems online."
let VOICE = "Daniel"
let DISPLAY_SECONDS: TimeInterval = 11.0
let FADE_SECONDS: TimeInterval = 1.0
// Karşılama artık HUD içinde Jarvis'in kendi ses dosyasıyla (voice.mp3) çalınıyor.

final class HUDController: NSObject, WKNavigationDelegate {
    var windows: [NSWindow] = []
    var keyMonitor: Any?
    var isShowing = false
    var sayProcess: Process?

    func htmlURL() -> URL? {
        // Önce bundle Resources, sonra geliştirme yolu (~/.jarvis/hud) denenir.
        if let u = Bundle.main.url(forResource: "index", withExtension: "html") {
            return u
        }
        let dev = ("~/.jarvis/hud/index.html" as NSString).expandingTildeInPath
        if FileManager.default.fileExists(atPath: dev) {
            return URL(fileURLWithPath: dev)
        }
        return nil
    }

    func show() {
        // Üst üste tetiklenmeyi engelle.
        if isShowing { return }
        guard let url = htmlURL() else {
            NSLog("JARVIS: index.html bulunamadı")
            return
        }
        isShowing = true

        let cfg = WKWebViewConfiguration()
        cfg.mediaTypesRequiringUserActionForPlayback = []

        for screen in NSScreen.screens {
            let frame = screen.frame
            let win = NSWindow(contentRect: frame,
                               styleMask: .borderless,
                               backing: .buffered,
                               defer: false)
            win.isOpaque = false
            win.backgroundColor = .clear
            win.level = .screenSaver
            win.ignoresMouseEvents = true
            win.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
            win.hasShadow = false
            win.alphaValue = 1.0

            let web = WKWebView(frame: NSRect(origin: .zero, size: frame.size), configuration: cfg)
            web.navigationDelegate = self
            web.setValue(false, forKey: "drawsBackground") // saydam arkaplan
            web.autoresizingMask = [.width, .height]
            web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())

            win.contentView = web
            win.setFrame(frame, display: true)
            win.orderFrontRegardless()
            windows.append(win)
        }

        // Esc ile erken kapatma.
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] ev in
            if ev.keyCode == 53 { self?.dismiss() }
            return ev
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + DISPLAY_SECONDS) { [weak self] in
            self?.dismiss()
        }
    }

    func speak() {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/say")
        p.arguments = ["-v", VOICE, GREETING]
        try? p.run()
        sayProcess = p
    }

    func dismiss() {
        guard isShowing else { return }
        if let m = keyMonitor { NSEvent.removeMonitor(m); keyMonitor = nil }

        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = FADE_SECONDS
            for w in self.windows { w.animator().alphaValue = 0.0 }
        }, completionHandler: {
            for w in self.windows { w.orderOut(nil) }
            self.windows.removeAll()
            self.isShowing = false
        })
    }
}

// MARK: - Conversational assistant (push-to-talk overlay + WS link to jarvis-core)

let WS_URL = URL(string: "ws://127.0.0.1:8765")!

final class AssistantController: NSObject {
    var window: NSWindow?
    var ws: URLSessionWebSocketTask?
    var session: URLSession!
    var active = false      // overlay shown
    var listening = false   // mic currently open
    var keyMonitor: Any?
    var hotKeyRef: EventHotKeyRef?

    override init() {
        super.init()
        session = URLSession(configuration: .default)
        connect()
    }

    // ---- WebSocket link to the Python core ----
    func connect() {
        ws = session.webSocketTask(with: WS_URL)
        ws?.resume()
        receive()
    }
    func receive() {
        ws?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .failure:
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { self.connect() }
            case .success(let msg):
                if case .string(let text) = msg, text.replacingOccurrences(of: " ", with: "").contains("\"type\":\"end\"") {
                    DispatchQueue.main.async { self.hideOverlay() }
                }
                self.receive()
            }
        }
    }
    func send(_ json: String) { ws?.send(.string(json)) { _ in } }

    // ---- push-to-talk toggle: tap to start, tap again to stop & process ----
    @objc func toggle() {
        if !active {
            showOverlay()
            active = true
            listening = true
            send("{\"type\":\"ptt\",\"state\":\"down\"}")
        } else if listening {
            listening = false
            send("{\"type\":\"ptt\",\"state\":\"up\"}")   // overlay stays until core sends "end"
        }
    }

    func assistantURL() -> URL? {
        if let u = Bundle.main.url(forResource: "assistant", withExtension: "html") { return u }
        for p in ["~/.jarvis/hud/assistant.html", "~/jarvis-unlock-hud/hud/assistant.html"] {
            let path = (p as NSString).expandingTildeInPath
            if FileManager.default.fileExists(atPath: path) { return URL(fileURLWithPath: path) }
        }
        return nil
    }

    func showOverlay() {
        guard window == nil, let url = assistantURL(),
              let screen = NSScreen.main else { return }
        let frame = screen.frame
        let win = NSWindow(contentRect: frame, styleMask: .borderless, backing: .buffered, defer: false)
        win.isOpaque = false; win.backgroundColor = .clear; win.level = .screenSaver
        win.ignoresMouseEvents = true
        win.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .stationary]
        win.hasShadow = false
        let cfg = WKWebViewConfiguration()
        cfg.mediaTypesRequiringUserActionForPlayback = []
        let web = WKWebView(frame: NSRect(origin: .zero, size: frame.size), configuration: cfg)
        web.setValue(false, forKey: "drawsBackground")
        web.autoresizingMask = [.width, .height]
        web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        win.contentView = web
        win.orderFrontRegardless()
        window = win
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] ev in
            if ev.keyCode == 53 { self?.send("{\"type\":\"cancel\"}"); self?.hideOverlay() }
            return ev
        }
    }

    func hideOverlay() {
        active = false; listening = false
        if let m = keyMonitor { NSEvent.removeMonitor(m); keyMonitor = nil }
        guard let win = window else { return }
        NSAnimationContext.runAnimationGroup({ ctx in
            ctx.duration = 0.6
            win.animator().alphaValue = 0.0
        }, completionHandler: {
            win.orderOut(nil)
            self.window = nil
        })
    }

    // ---- register ⌥⌘J system-wide (Carbon, no Accessibility permission) ----
    func registerHotkey() {
        let hotKeyID = EventHotKeyID(signature: OSType(0x4a525653), id: 1) // 'JRVS'
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard),
                                 eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { (_, _, userData) -> OSStatus in
            let ctrl = Unmanaged<AssistantController>.fromOpaque(userData!).takeUnretainedValue()
            DispatchQueue.main.async { ctrl.toggle() }
            return noErr
        }, 1, &spec, Unmanaged.passUnretained(self).toOpaque(), nil)
        RegisterEventHotKey(UInt32(kVK_ANSI_J), UInt32(cmdKey | optionKey),
                            hotKeyID, GetApplicationEventTarget(), 0, &hotKeyRef)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    let hud = HUDController()
    let assistant = AssistantController()

    func applicationDidFinishLaunching(_ note: Notification) {
        NSApp.setActivationPolicy(.accessory) // dock'ta görünmez
        if !CommandLine.arguments.contains("--demo") {
            assistant.registerHotkey()   // ⌥⌘J push-to-talk
        }

        let dnc = DistributedNotificationCenter.default()
        // Asıl tetikleyici: kilit açıldı.
        dnc.addObserver(self, selector: #selector(onUnlock),
                        name: NSNotification.Name("com.apple.screenIsUnlocked"), object: nil)
        // Yedek: ekran koruyucu durdu (bazı yapılandırmalarda gelir).
        dnc.addObserver(self, selector: #selector(onUnlock),
                        name: NSNotification.Name("com.apple.screensaver.didstop"), object: nil)

        // Demo modu: kilidi beklemeden hemen göster, dizi bitince çık.
        if CommandLine.arguments.contains("--demo") {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
                self?.hud.show()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + DISPLAY_SECONDS + FADE_SECONDS + 1.0) {
                NSApp.terminate(nil)
            }
        }
    }

    @objc func onUnlock() {
        hud.show()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
