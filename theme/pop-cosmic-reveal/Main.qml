import QtQuick 2.15
import QtMultimedia 5.15

Rectangle {
    id: root
    color: "#141210"

    property string selectedUser: ""
    property string selectedDisplayName: ""
    property bool authenticating: false

    // Fira Sans is a system font (already installed on Pop!_OS), resolved via fontconfig.

    // ---------------------------------------------------------------
    // Background: grayscale by default, color reveals on successful login
    // ---------------------------------------------------------------

    // Static fallback frame, shown until the video reports it has a frame ready.
    Image {
        id: bgFallback
        anchors.fill: parent
        source: "assets/wallpaper-color.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
    }

    Video {
        id: bgVideo
        anchors.fill: parent
        source: "assets/wallpaper.mp4"
        fillMode: VideoOutput.PreserveAspectCrop
        autoPlay: true
        muted: true
        loops: MediaPlayer.Infinite
    }

    // Grayscale still frame masks the color video until a successful login.
    Image {
        id: bgGray
        anchors.fill: parent
        source: "assets/wallpaper-gray.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        Behavior on opacity { NumberAnimation { duration: 900; easing.type: Easing.OutCubic } }
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

    Column {
        id: authView
        visible: selectedUser !== ""
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: 40
        spacing: 18

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 108; height: 108; radius: 54
            color: "#2b2723"
            border.width: 2
            border.color: "#e07828"

            Item {
                anchors.centerIn: parent
                width: 46; height: 46
                Rectangle { x: 15; y: 2; width: 16; height: 16; radius: 8; color: "#f7f4f1" }
                Rectangle { x: 4; y: 22; width: 38; height: 22; radius: 11; color: "#f7f4f1" }
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
            anchors.horizontalCenter: parent.horizontalCenter
            width: 280; height: 46; radius: 23
            color: "#0fffffff"
            border.width: 1
            border.color: passwordField.activeFocus ? "#99e07828" : "#26ffffff"

            TextInput {
                id: passwordField
                anchors.fill: parent
                anchors.margins: 2
                echoMode: TextInput.Password
                color: "#f7f4f1"
                font.family: "Fira Sans"
                font.pixelSize: 16
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                clip: true
                onAccepted: doLogin()
            }

            Text {
                anchors.centerIn: parent
                text: "Senha"
                color: "#4df7f4f1"
                font.family: "Fira Sans"
                font.pixelSize: 16
                visible: passwordField.text.length === 0
            }
        }

        Text {
            id: errorText
            anchors.horizontalCenter: parent.horizontalCenter
            color: "#e8926a"
            font.family: "Fira Sans"
            font.pixelSize: 13
            height: 18
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
            bgGray.opacity = 0
        }
        function onLoginFailed() {
            authenticating = false
            errorText.text = "Senha incorreta"
            passwordField.text = ""
            passwordField.forceActiveFocus()
        }
    }

    // ---------------------------------------------------------------
    // Power menu
    // ---------------------------------------------------------------

    Rectangle {
        id: powerBtn
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        anchors.margins: 44
        width: 44; height: 44; radius: 22
        color: powerMouse.containsMouse ? "#14ffffff" : "#08ffffff"
        border.width: 1
        border.color: "#24ffffff"

        Text {
            anchors.centerIn: parent
            text: "⏻"
            color: "#c8f7f4f1"
            font.pixelSize: 18
        }

        MouseArea {
            id: powerMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: powerMenu.visible = !powerMenu.visible
        }
    }

    Column {
        id: powerMenu
        visible: false
        anchors.bottom: powerBtn.top
        anchors.right: powerBtn.right
        anchors.bottomMargin: 12
        spacing: 2

        Rectangle {
            width: 176; height: childrenRect.height + 12
            radius: 14
            color: "#f0211d19"
            border.width: 1
            border.color: "#1fffffff"

            Column {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 2

                Repeater {
                    model: [
                        { label: "Suspender", enabled: sddm.canSuspend, action: function() { sddm.suspend() } },
                        { label: "Reiniciar", enabled: sddm.canReboot, action: function() { sddm.reboot() } },
                        { label: "Desligar", enabled: sddm.canPowerOff, action: function() { sddm.powerOff() } }
                    ]

                    Rectangle {
                        visible: modelData.enabled
                        width: parent.width
                        height: visible ? 38 : 0
                        radius: 9
                        color: itemMouse.containsMouse ? "#12ffffff" : "transparent"

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.label
                            color: "#d9f7f4f1"
                            font.family: "Fira Sans"
                            font.pixelSize: 14
                        }

                        MouseArea {
                            id: itemMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                powerMenu.visible = false
                                modelData.action()
                            }
                        }
                    }
                }
            }
        }
    }

    MouseArea {
        z: -1
        anchors.fill: parent
        onClicked: powerMenu.visible = false
        enabled: powerMenu.visible
    }

}
