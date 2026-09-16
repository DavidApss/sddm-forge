import QtQuick 2.15
import QtMultimedia 5.15
import PopGreeterActions 1.0

Rectangle {
    id: root
    color: "#141210"

    property string selectedUser: ""
    property string selectedDisplayName: ""
    property bool authenticating: false
    property var userList: []

    focus: true
    Keys.onPressed: {
        if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter) && selectedUser === "") {
            selectDefaultUser()
            event.accepted = true
        }
    }

    function selectDefaultUser() {
        if (userList.length === 0) return
        var u = userList[0]
        selectedUser = u.name
        selectedDisplayName = u.realName !== "" ? u.realName : u.name
        passwordField.text = ""
        errorText.text = ""
        passwordField.forceActiveFocus()
    }

    PopGreeterActions { id: popActions }

    // Fira Sans is a system font (already installed on Pop!_OS), resolved via fontconfig.

    // ---------------------------------------------------------------
    // Background: grayscale fades to color as you type.
    // ---------------------------------------------------------------

    // Static fallback frame, shown until the video reports it has a frame ready.
    Image {
        id: bgFallback
        anchors.fill: parent
        source: "assets/wallpaper1-color.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }

    Video {
        id: bgVideo
        anchors.fill: parent
        source: "assets/wallpaper1.mp4"
        fillMode: VideoOutput.PreserveAspectCrop
        autoPlay: true
        muted: true
        loops: MediaPlayer.Infinite
    }

    // Grayscale mask over the color video. Fades fast as you type (a tease),
    // jumps to fully revealed the moment you submit, and dims back down on a
    // failed login or if you clear the field. sddm-greeter runs one QML
    // engine per screen, so this screen's own typing drives popActions.reveal
    // (shared process-wide, see the plugin) and every screen's mask reads it
    // back - that's what keeps a multi-monitor setup in sync.
    property bool sessionRevealed: false
    property real typingReveal: {
        if (sessionRevealed || authenticating) return 1
        if (selectedUser === "") return 0
        return Math.min(passwordField.text.length / 5, 1) * 0.7
    }
    onTypingRevealChanged: popActions.reveal = typingReveal

    Image {
        id: bgGray
        anchors.fill: parent
        source: "assets/wallpaper1-gray.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        opacity: 1 - Math.max(typingReveal, popActions.reveal)
        Behavior on opacity { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#00000000" }
            GradientStop { position: 0.62; color: "#00000000" }
            GradientStop { position: 1.0; color: "#73000000" }
        }
    }

    // ---------------------------------------------------------------
    // Wordmark
    // ---------------------------------------------------------------

    Row {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 44
        spacing: 10

        Rectangle {
            width: 18; height: 18; radius: 5
            color: "#e07828"
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: "pop!_os"
            color: "#e0ffffff"
            font.family: "Fira Sans"
            font.weight: Font.DemiBold
            font.pixelSize: 15
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // ---------------------------------------------------------------
    // Clock
    // ---------------------------------------------------------------

    property date now: new Date()
    Timer { interval: 1000; running: true; repeat: true; onTriggered: now = new Date() }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: root.height * 0.16
        spacing: 8

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: now.toLocaleTimeString(Qt.locale(), Locale.ShortFormat)
            color: "#f7f4f1"
            font.family: "Fira Sans"
            font.weight: Font.Bold
            font.pixelSize: Math.round(Math.min(116, root.width * 0.075))
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: now.toLocaleDateString(Qt.locale(), Locale.LongFormat)
            color: "#a6f7f4f1"
            font.family: "Fira Sans"
            font.pixelSize: 17
        }
    }

    // ---------------------------------------------------------------
    // User selection
    // ---------------------------------------------------------------

    Column {
        id: userView
        visible: selectedUser === ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 112
        spacing: 20

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Selecione seu usuário"
            color: "#8cf7f4f1"
            font.family: "Fira Sans"
            font.pixelSize: 14
        }

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 30

            Repeater {
                model: userModel

                Column {
                    spacing: 10
                    width: 76

                    Component.onCompleted: {
                        root.userList.push({ name: model.name, realName: model.realName })
                    }

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 68; height: 68; radius: 34
                        color: "#2b2723"
                        border.width: 2
                        border.color: "transparent"

                        // simple placeholder person glyph (avatar images need a Qt5
                        // circular-mask module we're deliberately not depending on)
                        Item {
                            anchors.centerIn: parent
                            width: 32; height: 32
                            Rectangle {
                                x: 10; y: 2; width: 12; height: 12; radius: 6
                                color: "#bfbab5"
                            }
                            Rectangle {
                                x: 3; y: 16; width: 26; height: 16
                                radius: 8
                                color: "#bfbab5"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                selectedUser = model.name
                                selectedDisplayName = model.realName !== "" ? model.realName : model.name
                                passwordField.text = ""
                                errorText.text = ""
                                passwordField.forceActiveFocus()
                            }
                        }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: model.realName !== "" ? model.realName : model.name
                        color: "#f7f4f1"
                        font.family: "Fira Sans"
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                        width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------
    // Authentication
    // ---------------------------------------------------------------

    Rectangle {
        id: authCard
        visible: selectedUser !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 30
        width: 340
        height: authColumn.height + 64
        radius: 22
        color: "#c7211d19"
        border.width: 1
        border.color: "#1effffff"

        Column {
            id: authColumn
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 32
            spacing: 16
            width: 280

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 92; height: 92; radius: 46
                color: "#2b2723"
                border.width: 2
                border.color: "#e07828"

                Item {
                    anchors.centerIn: parent
                    width: 40; height: 40
                    Rectangle { x: 13; y: 2; width: 14; height: 14; radius: 7; color: "#f7f4f1" }
                    Rectangle { x: 3; y: 19; width: 34; height: 19; radius: 10; color: "#f7f4f1" }
                }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: selectedDisplayName
                color: "#f7f4f1"
                font.family: "Fira Sans"
                font.weight: Font.DemiBold
                font.pixelSize: 18
            }

            Rectangle {
                width: parent.width; height: 46; radius: 23
                color: "#14ffffff"
                border.width: 1
                border.color: passwordField.activeFocus ? "#99e07828" : "#26ffffff"

                TextInput {
                    id: passwordField
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    echoMode: TextInput.Password
                    color: "#f7f4f1"
                    font.family: "Fira Sans"
                    font.pixelSize: 16
                    verticalAlignment: Text.AlignVCenter
                    clip: true
                    onAccepted: doLogin()
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 20
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Senha"
                    color: "#4df7f4f1"
                    font.family: "Fira Sans"
                    font.pixelSize: 16
                    visible: passwordField.text.length === 0
                }
            }

            Rectangle {
                width: parent.width; height: 44; radius: 22
                color: loginMouse.pressed ? "#c26620" : "#e07828"

                Text {
                    anchors.centerIn: parent
                    text: authenticating ? "Entrando…" : "Entrar"
                    color: "#1a1613"
                    font.family: "Fira Sans"
                    font.weight: Font.DemiBold
                    font.pixelSize: 15
                }

                MouseArea {
                    id: loginMouse
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: doLogin()
                }
            }

            Text {
                id: errorText
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#e8926a"
                font.family: "Fira Sans"
                font.pixelSize: 13
                height: 16
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Voltar"
                color: "#80f7f4f1"
                font.family: "Fira Sans"
                font.pixelSize: 13

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        selectedUser = ""
                        selectedDisplayName = ""
                        passwordField.text = ""
                        errorText.text = ""
                    }
                }
            }
        }
    }

    function doLogin() {
        if (selectedUser === "" || authenticating) return
        authenticating = true
        var sIndex = sessionModel.lastIndex >= 0 ? sessionModel.lastIndex : 0
        sddm.login(selectedUser, passwordField.text, sIndex)
    }

    Connections {
        target: sddm
        function onLoginSucceeded() {
            errorText.text = ""
            sessionRevealed = true
        }
        function onLoginFailed() {
            authenticating = false
            errorText.text = "Senha incorreta"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    // ---------------------------------------------------------------
    // Power actions - always visible, bottom-right
    // ---------------------------------------------------------------

    Row {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: 40
        spacing: 22

        Repeater {
            model: [
                { label: "Suspender", glyph: "☾", enabled: sddm.canSuspend, action: function() { sddm.suspend() } },
                { label: "Reiniciar", glyph: "↻", enabled: sddm.canReboot, action: function() { sddm.reboot() } },
                { label: "Desligar", glyph: "⏻", enabled: sddm.canPowerOff, action: function() { sddm.powerOff() } }
            ]

            Column {
                spacing: 6

                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 44; height: 44; radius: 22
                    color: powerItemMouse.containsMouse ? "#14ffffff" : "#08ffffff"
                    border.width: 1
                    border.color: "#24ffffff"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.glyph
                        color: "#c8f7f4f1"
                        font.pixelSize: 17
                    }

                    MouseArea {
                        id: powerItemMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: modelData.action()
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: modelData.label
                    color: "#8cf7f4f1"
                    font.family: "Fira Sans"
                    font.pixelSize: 11
                }
            }
        }
    }

    // ---------------------------------------------------------------
    // Emergency switch: revert to cosmic-greeter (bottom-left)
    // Two-tap confirm: first tap arms it, second tap (within 4s) fires
    // the narrowly-scoped, sudoers-gated revert script via the
    // PopGreeterActions plugin.
    // ---------------------------------------------------------------

    property bool revertArmed: false
    property bool revertFired: false

    Timer {
        id: revertDisarmTimer
        interval: 4000
        onTriggered: revertArmed = false
    }

    Item {
        id: revertSwitch
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.margins: 40
        width: revertRow.width
        height: revertRow.height
        opacity: revertFired ? 1 : 0.55

        Row {
            id: revertRow
            spacing: 10

            Rectangle {
                id: revertTrack
                width: 40; height: 22; radius: 11
                anchors.verticalCenter: parent.verticalCenter
                color: root.revertArmed ? "#e07828" : "#26ffffff"
                border.width: 1
                border.color: "#26ffffff"
                Behavior on color { ColorAnimation { duration: 150 } }

                Rectangle {
                    width: 18; height: 18; radius: 9
                    anchors.verticalCenter: parent.verticalCenter
                    x: root.revertArmed ? parent.width - width - 2 : 2
                    color: "#f7f4f1"
                    Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: root.revertFired ? "Revertendo para o COSMIC…" : (root.revertArmed ? "Toque de novo para confirmar" : "Usar login padrão do COSMIC")
                color: root.revertArmed ? "#e07828" : "#80f7f4f1"
                font.family: "Fira Sans"
                font.pixelSize: 12
            }
        }

        MouseArea {
            anchors.fill: parent
            anchors.margins: -8
            enabled: !root.revertFired
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                if (!root.revertArmed) {
                    root.revertArmed = true
                    revertDisarmTimer.restart()
                } else {
                    revertDisarmTimer.stop()
                    root.revertFired = true
                    var ok = popActions.revertToCosmic()
                    if (!ok) {
                        root.revertFired = false
                        root.revertArmed = false
                    }
                }
            }
        }
    }

}
