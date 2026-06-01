import Cocoa
import WebKit

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

final class AppDelegate: NSObject, NSApplicationDelegate {
    let hud = HUDController()

    func applicationDidFinishLaunching(_ note: Notification) {
        NSApp.setActivationPolicy(.accessory) // dock'ta görünmez

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
