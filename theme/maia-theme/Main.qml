import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtMultimedia
import Qt5Compat.GraphicalEffects

// ==========================================================================
// Tema Maia — interpretador de layout.json (sddm-forge).
// A árvore de componentes vem de `layoutProvider` (prévia) ou do arquivo
// layout.json ao lado deste Main.qml (greeter real, via XMLHttpRequest).
// Cores / fontes / fundo continuam em theme.conf (objeto `config`).
// ==========================================================================
Rectangle {
    id: root
    width: Screen.width
    height: Screen.height
    color: cfg.bgColor

    // ----------------------------------------------------------------------
    // Config visual (theme.conf)
    // ----------------------------------------------------------------------
    QtObject {
        id: cfg

        function str(v, def) {
            return (v === undefined || v === null || v === "") ? def : String(v)
        }
        function num(v, def) {
            var n = parseFloat(v)
            return isNaN(n) ? def : n
        }
        function boolTrue(v) { return String(v) !== "false" }

        readonly property string backgroundMode: str(config.backgroundMode, "video")
        readonly property url backgroundImage: Qt.resolvedUrl(str(config.background, "assets/background.jpeg"))
        readonly property url backgroundVideo: Qt.resolvedUrl(str(config.backgroundVideo, "assets/frieren-moon.mp4"))
        readonly property color bgColor: str(config.bgColor, "#0b0f14")
        readonly property int blurRadius: num(config.blurRadius, 24)
        readonly property int videoBlurRadius: num(config.videoBlurRadius, 4)
        readonly property real dimOpacity: num(config.dimOpacity, 0.40)

        readonly property color accent: str(config.accentColor, "#66d9ff")
        readonly property color accentDim: str(config.accentColorDim, "#55aacc")
        readonly property color textColor: str(config.textColor, "#ffffff")
        readonly property color subTextColor: str(config.subTextColor, "#b0c7d8")
        readonly property color errorColor: str(config.errorColor, "#ff8080")

        readonly property string fontFamily: str(config.fontFamily, "JetBrains Mono")
        readonly property int clockFontSize: num(config.clockFontSize, 68)
        readonly property int dateFontSize: num(config.dateFontSize, 18)
        readonly property int nameFontSize: num(config.nameFontSize, 26)

        readonly property int marginX: num(config.marginX, 56)
        readonly property int marginY: num(config.marginY, 56)
        readonly property int passwordWidth: num(config.passwordWidth, 280)

        readonly property string clockFormat: str(config.clockFormat, "hh:mm")
        readonly property string dateFormat: str(config.dateFormat, "dddd, d 'de' MMMM")
        readonly property string dateLocale: str(config.dateLocale, "pt_BR")

        readonly property string inputStyle: str(config.inputStyle, "underline")
        readonly property string buttonStyle: str(config.buttonStyle, "outline")
        readonly property string controlStyle: str(config.controlStyle, "text")
        readonly property string controlIcons: str(config.controlIcons, "off")  // off | only | label

        readonly property bool useVideo: backgroundMode === "video"
        readonly property bool useImage: backgroundMode === "image"
        readonly property bool useColorOnly: backgroundMode === "color"
    }

    // ----------------------------------------------------------------------
    // Estado compartilhado
    // ----------------------------------------------------------------------
    property var userList: []
    property int userIndex: 0
    property string selectedUser: userList.length > 0 ? userList[userIndex].name : ""

    property var sessionList: []
    property int sessionIndex: 0
    property string selectedSessionName: sessionList.length > 0 ? sessionList[sessionIndex] : ""

    property Item passwordField: null
    property string errorText: ""
    property bool showPassword: false
    property var now: new Date()

    // overrides opcionais por nó (accent / size / bold)
    function ovColor(node, dflt) {
        return (node && node.accent && node.accent !== "") ? node.accent : dflt
    }
    function ovSize(node, dflt) {
        return (node && node.size) ? node.size : dflt
    }
    function ovBold(node, dflt) {
        return (node && node.bold !== undefined) ? (node.bold === true || node.bold === "true") : dflt
    }

    property var layoutTree: parseLayout()
    onLayoutTreeChanged: syncPanels()   // reage a config.layoutJson
    property bool animate: false        // liga as transições depois do 1º frame
    readonly property bool previewMode: String(config.previewMode || "") === "1"

    function displayName(u) {
        if (!u)
            return "Usuário"
        return (u.realName && u.realName !== "") ? u.realName : u.name
    }
    function clearPassword() { if (passwordField) passwordField.text = "" }
    function submit() {
        sddm.login(selectedUser, passwordField ? passwordField.text : "", sessionIndex)
    }
    function cycleUser(step) {
        if (userList.length < 2)
            return
        userIndex = (userIndex + step + userList.length) % userList.length
        clearPassword()
        errorText = ""
    }
    function cycleSession(step) {
        if (sessionList.length < 2)
            return
        sessionIndex = (sessionIndex + step + sessionList.length) % sessionList.length
    }
    function ctlColor(btn) {
        if (btn.down)
            return cfg.accent
        return btn.hovered ? cfg.textColor : cfg.subTextColor
    }
    readonly property bool ctlOutline: cfg.controlStyle === "outline"
    readonly property bool ctlPill: cfg.controlStyle === "pill"
    readonly property bool ctlBoxed: ctlOutline || ctlPill
    function ctlBgColor(btn) {
        if (ctlPill)
            return btn.hovered ? Qt.rgba(1, 1, 1, 0.16) : Qt.rgba(1, 1, 1, 0.08)
        return "transparent"
    }

    // ----------------------------------------------------------------------
    // Layout: leitura e reação
    // ----------------------------------------------------------------------
    function parseLayout() {
        // fonte principal: string em base64 no theme.conf (o SDDM remove aspas
        // de valores, então JSON puro não sobreviveria). Reativa via `config`.
        try {
            var raw = config.layoutJson ? String(config.layoutJson) : ""
            if (raw.length > 0) {
                var txt = (raw.charAt(0) === "{") ? raw : Qt.atob(raw)
                return JSON.parse(txt)
            }
        } catch (e) {
            console.warn("config.layoutJson:", e)
        }
        // fallback: arquivo layout.json ao lado (temas antigos)
        try {
            var xhr = new XMLHttpRequest()
            xhr.open("GET", Qt.resolvedUrl("layout.json"), false)
            xhr.send()
            if (xhr.responseText && xhr.responseText.length > 0)
                return JSON.parse(xhr.responseText)
        } catch (e2) {
            console.warn("layout.json:", e2)
        }
        return { "version": 1, "root": [] }
    }

    function coord(v, base) {
        if (typeof v === "string" && v.slice(-1) === "%")
            return base * parseFloat(v) / 100
        var n = parseFloat(v)
        return isNaN(n) ? 0 : n
    }
    function sizeSpec(spec, base, content) {
        if (spec === "fill")
            return base
        if (typeof spec === "string" && spec.slice(-1) === "%")
            return base * parseFloat(spec) / 100
        var n = parseFloat(spec)
        if (!isNaN(n) && String(spec) !== "auto")
            return n
        return content
    }
    function panelX(node, item) {
        if (node.width === "fill")
            return 0
        var p = node.position
        if (p && typeof p === "object")
            return coord(p.x, root.width)
        p = String(p)
        if (p.indexOf("left") !== -1)
            return cfg.marginX
        if (p.indexOf("right") !== -1)
            return root.width - item.width - cfg.marginX
        return (root.width - item.width) / 2   // *-center e "center"
    }
    function panelY(node, item) {
        if (node.height === "fill")
            return 0
        var p = node.position
        if (p && typeof p === "object")
            return coord(p.y, root.height)
        p = String(p)
        if (p.indexOf("top") !== -1)
            return cfg.marginY
        if (p.indexOf("bottom") !== -1)
            return root.height - item.height - cfg.marginY
        return (root.height - item.height) / 2   // "center", "center-left/right"
    }
    function justifyOffset(justify, avail, content, pad) {
        var free = avail - 2 * pad - content
        if (free <= 0)
            return pad
        if (justify === "center")
            return pad + free / 2
        if (justify === "end")
            return pad + free
        return pad
    }
    function elementFor(type) {
        switch (type) {
        case "clock":         return e_clock
        case "date":          return e_date
        case "text":          return e_text
        case "spacer":        return e_spacer
        case "separator":     return e_separator
        case "usernameRow":   return e_usernameRow
        case "userHandle":    return e_userHandle
        case "avatar":        return e_avatar
        case "password":      return e_password
        case "passwordToggle": return e_passwordToggle
        case "loginButton":   return e_loginButton
        case "sessionButton": return e_sessionButton
        case "sessionName":   return e_sessionName
        case "rebootButton":  return e_rebootButton
        case "powerButton":   return e_powerButton
        case "suspendButton": return e_suspendButton
        case "errorMessage":  return e_errorMessage
        }
        return e_missing
    }

    Component.onCompleted: {
        var arr = []
        for (var i = 0; i < userModel.count; i++) {
            var idx = userModel.index(i, 0)
            arr.push({
                name: userModel.data(idx, Qt.UserRole + 1) || "",
                realName: userModel.data(idx, Qt.UserRole + 2) || "",
                icon: userModel.data(idx, Qt.UserRole + 4) || ""
            })
        }
        userList = arr
        for (var j = 0; j < arr.length; j++) {
            if (arr[j].name === userModel.lastUser) {
                userIndex = j
                break
            }
        }

        var sarr = []
        for (var s = 0; s < sessionModel.count; s++) {
            var sidx = sessionModel.index(s, 0)
            var sname = sessionModel.data(sidx, Qt.UserRole + 4)
            sarr.push(sname && sname !== "" ? sname : ("Sessão " + (s + 1)))
        }
        sessionList = sarr
        if (sessionModel.lastIndex >= 0 && sessionModel.lastIndex < sarr.length)
            sessionIndex = sessionModel.lastIndex

        root.syncPanels()
        enableAnim.start()
    }

    Timer {
        id: enableAnim
        interval: 250
        onTriggered: root.animate = true
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = new Date()
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.errorText = "Usuário ou senha inválidos"
            root.clearPassword()
        }
    }

    // ----------------------------------------------------------------------
    // Modelo de painéis sincronizado in-place (mantém os delegates vivos →
    // mudança só de propriedade anima; reordenar/criar/remover recria).
    // ----------------------------------------------------------------------
    ListModel { id: panelModel }

    function syncPanels() {
        var tree = root.layoutTree
        var arr = (tree && tree.root) ? tree.root : []
        var same = arr.length === panelModel.count
        if (same) {
            for (var i = 0; i < arr.length; i++) {
                if (panelModel.get(i).nodeId !== arr[i].id) {
                    same = false
                    break
                }
            }
        }
        if (same) {
            for (var j = 0; j < arr.length; j++)
                panelModel.setProperty(j, "nodeJson", JSON.stringify(arr[j]))
        } else {
            panelModel.clear()
            for (var k = 0; k < arr.length; k++)
                panelModel.append({ nodeId: arr[k].id, nodeJson: JSON.stringify(arr[k]) })
        }
    }

    // ======================================================================
    // Fundo
    // ======================================================================
    Item {
        id: bgLayer
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: cfg.bgColor
        }
        Image {
            id: imageBg
            anchors.fill: parent
            source: cfg.backgroundImage
            fillMode: Image.PreserveAspectCrop
            visible: cfg.useImage
            cache: true
            asynchronous: true
        }
        VideoOutput {
            id: videoBg
            anchors.fill: parent
            fillMode: VideoOutput.PreserveAspectCrop
            visible: cfg.useVideo
        }
        MediaPlayer {
            id: player
            source: cfg.backgroundVideo
            videoOutput: videoBg
            audioOutput: AudioOutput { muted: true }
            loops: MediaPlayer.Infinite
            autoPlay: cfg.useVideo
        }
    }

    FastBlur {
        anchors.fill: parent
        visible: !cfg.useColorOnly
        source: bgLayer
        radius: cfg.useVideo ? cfg.videoBlurRadius : cfg.blurRadius
    }

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, cfg.dimOpacity)
    }

    Rectangle {
        anchors.top: parent.top
        width: parent.width
        height: 180
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#99000000" }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // ======================================================================
    // Interpretador da árvore
    // ======================================================================
    Repeater {
        model: panelModel
        delegate: Loader {
            required property string nodeJson
            sourceComponent: panelComponent
            onLoaded: {
                item.nodeJson = Qt.binding(function () { return nodeJson })
                // painel raiz: posiciona sozinho na tela. Sub-painel não passa
                // por aqui — flui dentro do Grid do pai.
                item.x = Qt.binding(function () { return root.panelX(item.n, item) })
                item.y = Qt.binding(function () { return root.panelY(item.n, item) })
            }
        }
    }

    Component {
        id: panelComponent

        Item {
            id: pnl
            property string nodeJson: ""
            // sub-painel: setado pelo Loader do pai. Muda como posiciona/mede.
            property Item parentPanel: null
            readonly property bool nested: parentPanel !== null
            readonly property var n: {
                try { return JSON.parse(nodeJson) } catch (e) { return ({}) }
            }
            readonly property int padX: (n.paddingX !== undefined && n.paddingX !== null)
                                        ? n.paddingX : (n.padding || 0)
            readonly property int padY: (n.paddingY !== undefined && n.paddingY !== null)
                                        ? n.paddingY : (n.padding || 0)
            readonly property var kids: n.children || []
            readonly property int blurAmt: n.blur || 0
            // base p/ larguras/alturas em % e "fill": tela (raiz) ou o pai (sub)
            readonly property real baseW: nested ? parentPanel.width : root.width
            readonly property real baseH: nested ? parentPanel.height : root.height

            clip: realBlur

            implicitWidth: lay.implicitWidth + 2 * padX
            implicitHeight: lay.implicitHeight + 2 * padY
            width: root.sizeSpec(n.width || "auto", baseW, implicitWidth)
            height: root.sizeSpec(n.height || "auto", baseH, implicitHeight)
            // x/y: painel raiz é posicionado pelo Loader de cima; sub-painel é
            // posicionado pelo Grid do pai — nos dois casos, nada de bind aqui.

            Behavior on x { enabled: root.animate; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            Behavior on y { enabled: root.animate; NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            Behavior on width { enabled: root.animate; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
            Behavior on height { enabled: root.animate; NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }

            opacity: 0
            Component.onCompleted: opacity = 1
            Behavior on opacity { NumberAnimation { duration: 160 } }

            // --- vidro fosco (blur do fundo atrás do painel) ---
            // Greeter real (GPU): MultiEffect (blur gaussiano de verdade,
            // suave — não o box-blur do FastBlur) sobre o bgLayer inteiro,
            // recortado ao painel pelo `clip`. É o mesmo efeito "vidro" do
            // Sugar Candy / Makima-SDDM.
            readonly property bool realBlur: pnl.blurAmt > 0 && !root.previewMode
            // blurAmt 0..100 -> força do frost. blur satura em ~70%; acima
            // disso o multiplier espalha mais sem virar mancha.
            readonly property real blurAmount: Math.min(1.0, pnl.blurAmt / 100 * 1.5)
            readonly property real blurMul: 0.7 + pnl.blurAmt / 100 * 2.3
            MultiEffect {
                visible: pnl.realBlur
                x: -pnl.x; y: -pnl.y; width: root.width; height: root.height
                source: bgLayer
                blurEnabled: pnl.realBlur
                blur: pnl.blurAmount
                blurMax: 64
                blurMultiplier: pnl.blurMul
                autoPaddingEnabled: false
            }
            // Prévia (renderer por software, sem shaders): aproximação —
            // renderiza o fundo em baixa resolução e deixa o upscale bilinear
            // borrar. Não é Gaussian, mas parece muito mais com blur.
            Item {
                anchors.fill: parent
                clip: true
                visible: pnl.blurAmt > 0 && root.previewMode
                readonly property int fac: Math.max(2, Math.round(pnl.blurAmt / 100 * 26))
                Image {
                    x: -pnl.x
                    y: -pnl.y
                    width: root.width
                    height: root.height
                    source: cfg.backgroundImage
                    fillMode: Image.PreserveAspectCrop
                    sourceSize.width: Math.max(8, Math.round(root.width / parent.fac))
                    smooth: true
                    mipmap: true
                    cache: true
                }
            }
            // lavagem de cor (tint / bg) — aceita #aarrggbb
            Rectangle {
                anchors.fill: parent
                radius: pnl.n.radius || 0
                readonly property string t: (pnl.n.tint && pnl.n.tint !== "")
                                            ? pnl.n.tint
                                            : (pnl.n.bg || "")
                visible: t !== ""
                color: t !== "" ? t : "transparent"
            }
            // escurecer (preto)
            Rectangle {
                anchors.fill: parent
                radius: pnl.n.radius || 0
                visible: (pnl.n.dim || 0) > 0
                color: Qt.rgba(0, 0, 0, Math.min(1, (pnl.n.dim || 0) / 100))
            }
            // granulado (efeito vidro) — bem sutil, tipo acrílico
            Image {
                anchors.fill: parent
                visible: (pnl.n.noise || 0) > 0
                source: (pnl.n.noise || 0) > 0
                        ? Qt.resolvedUrl("assets/noise.png") : ""
                fillMode: Image.Tile
                opacity: Math.min(0.25, (pnl.n.noise || 0) / 100 * 0.25)
                cache: true
            }
            // filete de borda (vidro)
            Rectangle {
                anchors.fill: parent
                radius: pnl.n.radius || 0
                color: "transparent"
                visible: pnl.n.border && pnl.n.border !== ""
                       && (pnl.n.borderWidth === undefined || pnl.n.borderWidth > 0)
                border.width: pnl.n.borderWidth !== undefined ? pnl.n.borderWidth : 1
                border.color: (pnl.n.border && pnl.n.border !== "")
                              ? pnl.n.border : "transparent"
            }

            // --- conteúdo ---
            Grid {
                id: lay
                x: (pnl.n.orientation === "row")
                   ? root.justifyOffset(pnl.n.justify, pnl.width, lay.width, pnl.padX)
                   : pnl.padX
                y: (pnl.n.orientation === "row")
                   ? pnl.padY
                   : root.justifyOffset(pnl.n.justify, pnl.height, lay.height, pnl.padY)
                width: pnl.width - 2 * pnl.padX
                columns: (pnl.n.orientation === "row") ? 999 : 1
                spacing: pnl.n.gap || 0
                horizontalItemAlignment: pnl.n.align === "center" ? Grid.AlignHCenter
                                       : pnl.n.align === "end" ? Grid.AlignRight
                                       : Grid.AlignLeft
                verticalItemAlignment: pnl.n.align === "center" ? Grid.AlignVCenter
                                     : pnl.n.align === "end" ? Grid.AlignBottom
                                     : Grid.AlignTop

                move: Transition {
                    enabled: root.animate
                    NumberAnimation { properties: "x,y"; duration: 200; easing.type: Easing.OutCubic }
                }
                add: Transition {
                    enabled: root.animate
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 }
                }

                Repeater {
                    model: pnl.kids
                    delegate: Loader {
                        required property var modelData
                        sourceComponent: (modelData.type === "panel")
                                         ? panelComponent
                                         : root.elementFor(modelData.type)
                        onLoaded: {
                            if (!item)
                                return
                            if (modelData.type === "panel") {
                                item.parentPanel = pnl
                                item.nodeJson = JSON.stringify(modelData)
                                return
                            }
                            if ("node" in item)
                                item.node = modelData
                            if ("orientation" in item)
                                item.orientation = pnl.n.orientation || "column"
                        }
                    }
                }
            }
        }
    }

    // ======================================================================
    // Ícone vetorial simples (Canvas) — power / restart / sleep / session
    // ======================================================================
    component GlyphIcon: Canvas {
        property string kind: "power"
        property color color: cfg.subTextColor
        property int size: 15
        implicitWidth: size
        implicitHeight: size
        onColorChanged: requestPaint()
        onKindChanged: requestPaint()
        onWidthChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.strokeStyle = color
            ctx.fillStyle = color
            ctx.lineWidth = Math.max(1.4, size / 10)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            var c = size / 2
            var r = size * 0.32
            if (kind === "power") {
                ctx.beginPath()
                ctx.arc(c, c + 1, r, -Math.PI * 0.30, Math.PI * 1.30)
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(c, c - r)
                ctx.lineTo(c, c + 1)
                ctx.stroke()
            } else if (kind === "restart") {
                ctx.beginPath()
                ctx.arc(c, c, r, Math.PI * 0.55, Math.PI * 2.05)
                ctx.stroke()
                var a = Math.PI * 0.55
                var ex = c + r * Math.cos(a)
                var ey = c + r * Math.sin(a)
                ctx.beginPath()
                ctx.moveTo(ex, ey)
                ctx.lineTo(ex - size * 0.16, ey - size * 0.02)
                ctx.moveTo(ex, ey)
                ctx.lineTo(ex - size * 0.02, ey - size * 0.18)
                ctx.stroke()
            } else if (kind === "sleep") {
                ctx.beginPath()
                ctx.arc(c + r * 0.35, c, r, Math.PI * 0.35, Math.PI * 1.65)
                ctx.stroke()
            } else {  // session — monitor/display
                ctx.strokeRect(c - r, c - r * 0.75, r * 2, r * 1.5)
                ctx.beginPath()
                ctx.moveTo(c - r * 0.5, c + r * 0.95)
                ctx.lineTo(c + r * 0.5, c + r * 0.95)
                ctx.stroke()
            }
        }
    }

    // ======================================================================
    // Elementos (folhas)
    // ======================================================================
    Component {
        id: e_clock
        Text {
            property var node
            text: Qt.formatTime(root.now, cfg.clockFormat)
            color: root.ovColor(node, cfg.textColor)
            font.pixelSize: root.ovSize(node, cfg.clockFontSize)
            font.bold: root.ovBold(node, true)
            font.family: cfg.fontFamily
        }
    }

    Component {
        id: e_date
        Text {
            property var node
            text: {
                var f = Qt.locale(cfg.dateLocale).toString(root.now, cfg.dateFormat)
                return f.charAt(0).toUpperCase() + f.slice(1)
            }
            color: root.ovColor(node, cfg.subTextColor)
            font.pixelSize: root.ovSize(node, cfg.dateFontSize)
            font.bold: root.ovBold(node, false)
            font.family: cfg.fontFamily
        }
    }

    Component {
        id: e_text
        Text {
            property var node
            text: (node && node.text !== undefined) ? node.text : ""
            color: root.ovColor(node, cfg.subTextColor)
            font.pixelSize: root.ovSize(node, 16)
            font.bold: root.ovBold(node, false)
            font.family: cfg.fontFamily
        }
    }

    Component {
        id: e_spacer
        Item {
            property var node
            implicitWidth: (node && node.size) ? node.size : 20
            implicitHeight: (node && node.size) ? node.size : 20
        }
    }

    Component {
        id: e_separator
        Item {
            property var node
            property string orientation: "column"
            readonly property int len: (node && node.size) ? node.size : 40
            implicitWidth: orientation === "row" ? 1 : len
            implicitHeight: orientation === "row" ? len : 1
            Rectangle {
                anchors.centerIn: parent
                width: parent.implicitWidth
                height: parent.implicitHeight
                color: root.ovColor(parent.node, cfg.accentDim)
                opacity: 0.5
            }
        }
    }

    Component {
        id: e_avatar
        Item {
            property var node
            readonly property int sz: (node && node.size) ? node.size : 76
            readonly property var u: root.userList.length > 0 ? root.userList[root.userIndex] : null
            implicitWidth: sz
            implicitHeight: sz

            Rectangle {
                id: circle
                anchors.fill: parent
                radius: width / 2
                color: Qt.rgba(1, 1, 1, 0.10)
                border.width: 1
                border.color: cfg.accentDim
            }
            Text {   // fallback: inicial
                anchors.centerIn: parent
                visible: img.status !== Image.Ready
                text: root.displayName(u).charAt(0).toUpperCase()
                color: cfg.textColor
                font.family: cfg.fontFamily
                font.bold: true
                font.pixelSize: parent.sz * 0.42
            }
            Image {
                id: img
                anchors.fill: parent
                source: (u && u.icon) ? u.icon : ""
                fillMode: Image.PreserveAspectCrop
                visible: false
            }
            OpacityMask {
                anchors.fill: parent
                source: img
                maskSource: circle
                visible: img.status === Image.Ready
            }
        }
    }

    Component {
        id: e_usernameRow
        Row {
            property var node
            readonly property bool carousel: !node || node.carousel !== false
            spacing: 12

            Text {
                id: unm
                text: root.displayName(root.userList.length > 0 ? root.userList[root.userIndex] : null)
                color: root.ovColor(parent.node, cfg.textColor)
                font.pixelSize: root.ovSize(parent.node, cfg.nameFontSize)
                font.family: cfg.fontFamily
                font.bold: root.ovBold(parent.node, true)
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -10
                    cursorShape: (carousel && root.userList.length > 1)
                                 ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.cycleUser(1)
                }
            }
            Text {
                visible: carousel && root.userList.length > 1
                anchors.verticalCenter: unm.verticalCenter
                text: "‹ " + (root.userIndex + 1) + "/" + root.userList.length + " ›"
                color: cfg.subTextColor
                font.pixelSize: 15
                font.family: cfg.fontFamily
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -8
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.cycleUser(1)
                }
            }
        }
    }

    Component {
        id: e_userHandle
        Text {
            property var node
            visible: {
                var u = root.userList.length > 0 ? root.userList[root.userIndex] : null
                return u && u.realName && u.realName !== "" && u.realName !== u.name
            }
            text: root.userList.length > 0 ? "@" + root.userList[root.userIndex].name : ""
            color: root.ovColor(node, cfg.subTextColor)
            font.pixelSize: root.ovSize(node, 13)
            font.family: cfg.fontFamily
        }
    }

    Component {
        id: e_password
        Item {
            id: pwWrap
            property var node
            readonly property string style: cfg.inputStyle
            readonly property bool boxed: style === "box" || style === "pill"
            implicitWidth: cfg.passwordWidth
            implicitHeight: style === "segmented" ? 22 : (boxed ? 42 : 40)

            Rectangle {   // sublinhado
                visible: pwWrap.style === "underline"
                anchors.bottom: parent.bottom
                width: parent.width
                height: 2
                color: pwf.activeFocus ? cfg.accent : cfg.accentDim
                opacity: pwf.activeFocus ? 1.0 : 0.8
            }
            Rectangle {   // caixa / pill
                visible: pwWrap.boxed
                anchors.fill: parent
                radius: pwWrap.style === "pill" ? height / 2 : 4
                color: Qt.rgba(1, 1, 1, 0.06)
                border.width: 1
                border.color: pwf.activeFocus ? cfg.accent : cfg.accentDim
            }
            Row {          // barra segmentada
                visible: pwWrap.style === "segmented"
                anchors.fill: parent
                spacing: 3
                Repeater {
                    model: 16
                    Rectangle {
                        width: (pwWrap.width - 15 * 3) / 16
                        height: parent.height
                        radius: 1
                        color: index < pwf.length ? cfg.accent : cfg.accentDim
                        opacity: index < pwf.length ? 1.0 : 0.35
                    }
                }
            }

            TextField {
                id: pwf
                anchors.fill: parent
                opacity: pwWrap.style === "segmented" ? 0 : 1
                echoMode: root.showPassword ? TextInput.Normal : TextInput.Password
                color: cfg.textColor
                font.family: cfg.fontFamily
                font.pixelSize: 16
                font.letterSpacing: (pwWrap.boxed || root.showPassword) ? 1 : 5
                selectByMouse: true
                verticalAlignment: TextInput.AlignVCenter
                leftPadding: pwWrap.boxed ? (pwWrap.style === "pill" ? 18 : 12) : -2
                rightPadding: pwWrap.boxed ? 12 : 0
                background: Item {}
                Keys.onUpPressed: root.cycleUser(-1)
                Keys.onDownPressed: root.cycleUser(1)
                onAccepted: root.submit()
                Component.onCompleted: {
                    root.passwordField = pwf
                    pwf.forceActiveFocus()
                }
            }
        }
    }

    Component {
        id: e_passwordToggle
        Row {
            property var node
            spacing: 7

            Rectangle {
                id: box
                width: 15
                height: 15
                anchors.verticalCenter: parent.verticalCenter
                radius: 3
                color: root.showPassword ? cfg.accent : "transparent"
                border.width: 1
                border.color: root.showPassword ? cfg.accent : cfg.accentDim
                Text {
                    anchors.centerIn: parent
                    visible: root.showPassword
                    text: "✓"
                    color: cfg.bgColor
                    font.pixelSize: 11
                }
                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -6
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.showPassword = !root.showPassword
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: (node && node.text) ? node.text : "Mostrar senha"
                color: cfg.subTextColor
                font.family: cfg.fontFamily
                font.pixelSize: 12
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.showPassword = !root.showPassword
                }
            }
        }
    }

    Component {
        id: e_loginButton
        Button {
            id: lb
            property var node
            readonly property bool filled: cfg.buttonStyle === "fill" || cfg.buttonStyle === "pill"
            implicitWidth: 140
            implicitHeight: 36
            text: "LOGIN"
            background: Rectangle {
                radius: cfg.buttonStyle === "pill" ? height / 2 : 6
                color: lb.filled ? (lb.hovered ? Qt.lighter(cfg.accent, 1.12) : cfg.accent)
                                 : "transparent"
                border.width: lb.filled ? 0 : 1
                border.color: lb.hovered ? cfg.accent : cfg.accentDim
            }
            contentItem: Text {
                text: lb.text
                color: lb.filled ? cfg.bgColor : cfg.textColor
                font.family: cfg.fontFamily
                font.bold: true
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            onClicked: root.submit()
        }
    }

    Component {
        id: e_errorMessage
        Text {
            property var node
            visible: root.errorText !== ""
            text: root.errorText
            color: root.ovColor(node, cfg.errorColor)
            font.pixelSize: root.ovSize(node, 12)
            font.family: cfg.fontFamily
        }
    }

    // botão de controle reutilizável (sessão / reiniciar / desligar / suspender)
    component ControlButton: Button {
        id: cbtn
        property var node
        property string glyph: "power"
        readonly property bool iconOn: cfg.controlIcons !== "off"
        readonly property bool iconOnly: cfg.controlIcons === "only"
        hoverEnabled: true
        padding: root.ctlBoxed ? 8 : 0
        leftPadding: root.ctlBoxed ? 12 : 0
        rightPadding: root.ctlBoxed ? 12 : 0
        background: Rectangle {
            color: root.ctlBgColor(cbtn)
            radius: root.ctlPill ? height / 2 : (root.ctlOutline ? 4 : 0)
            border.width: root.ctlOutline ? 1 : 0
            border.color: cfg.accentDim
        }
        contentItem: Column {
            spacing: 3
            GlyphIcon {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: cbtn.iconOn
                kind: cbtn.glyph
                color: root.ctlColor(cbtn)
                size: 17
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: !cbtn.iconOnly
                text: cbtn.text
                color: root.ctlColor(cbtn)
                font.family: cfg.fontFamily
                font.pixelSize: 13
                font.bold: true
            }
        }
    }

    Component {
        id: e_sessionButton
        ControlButton {
            glyph: "session"
            visible: root.sessionList.length > 0
            text: root.selectedSessionName.toUpperCase()
            onClicked: root.cycleSession(1)
        }
    }
    Component {
        id: e_rebootButton
        ControlButton {
            glyph: "restart"
            text: "REINICIAR"
            onClicked: sddm.reboot()
        }
    }
    Component {
        id: e_powerButton
        ControlButton {
            glyph: "power"
            text: "DESLIGAR"
            onClicked: sddm.powerOff()
        }
    }
    Component {
        id: e_suspendButton
        ControlButton {
            glyph: "sleep"
            text: "SUSPENDER"
            onClicked: sddm.suspend()
        }
    }

    Component {
        id: e_sessionName
        Text {
            property var node
            visible: root.selectedSessionName !== ""
            text: root.selectedSessionName
            color: root.ovColor(node, cfg.subTextColor)
            font.family: cfg.fontFamily
            font.pixelSize: root.ovSize(node, 13)
        }
    }

    Component {
        id: e_missing
        Text {
            property var node
            text: "?" + (node ? node.type : "")
            color: cfg.errorColor
            font.family: cfg.fontFamily
            font.pixelSize: 12
        }
    }
}
