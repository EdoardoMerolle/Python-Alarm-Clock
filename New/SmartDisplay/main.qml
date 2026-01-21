import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 1024
    height: 600
    title: "Smart Display"
    color: "#000000"

    property var editingAlarmId: null

    Connections {
        target: backend
        function onAlarmTriggered(message) { alarmPopup.open() }
    }

    // --- DYNAMIC BACKGROUND SLIDESHOW ---
    Item {
        id: slideshow
        anchors.fill: parent

        // Night Mode: Hide slideshow (Black screen)
        opacity: backend.isNightMode ? 0.0 : 1.0 
        Behavior on opacity { NumberAnimation { duration: 1000 } }

        property var images: backend.imageList
        property int currentIndex: 0
        property bool showBg1: true 

        Timer {
            interval: 10000 
            running: slideshow.images.length > 1 && !backend.isNightMode
            repeat: true
            onTriggered: {
                slideshow.currentIndex = (slideshow.currentIndex + 1) % slideshow.images.length
                var nextSource = slideshow.images[slideshow.currentIndex]
                
                if (slideshow.showBg1) {
                    bg2.source = nextSource
                } else {
                    bg1.source = nextSource
                }
                slideshow.showBg1 = !slideshow.showBg1
            }
        }

        Image {
            id: bg1
            anchors.fill: parent
            source: slideshow.images.length > 0 ? slideshow.images[0] : "" 
            fillMode: Image.PreserveAspectCrop
            opacity: slideshow.showBg1 ? 1.0 : 0.0 
            Behavior on opacity { NumberAnimation { duration: 2000 } } 
        }

        Image {
            id: bg2
            anchors.fill: parent
            source: "" 
            fillMode: Image.PreserveAspectCrop
            opacity: slideshow.showBg1 ? 0.0 : 1.0 
            Behavior on opacity { NumberAnimation { duration: 2000 } }
        }

        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: 0.2 
        }
    }

    // --- ALARM ALERT POPUP ---
    Popup {
        id: alarmPopup
        width: parent.width * 0.95
        height: parent.height * 0.85
        anchors.centerIn: parent
        modal: true
        closePolicy: Popup.NoAutoClose
        background: Rectangle { color: "#EE000000"; radius: 25; border.color: "#555"; border.width: 2 }

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 40
            Text { text: backend.currentTime; color: "white"; font.pixelSize: 140; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            Text { text: "WAKE UP"; color: "#FF4444"; font.pixelSize: 70; font.weight: Font.Black; Layout.alignment: Qt.AlignHCenter }
            RowLayout {
                spacing: 60
                Button {
                    text: "SNOOZE"
                    Layout.preferredWidth: 260; Layout.preferredHeight: 100
                    background: Rectangle { color: "#444444"; radius: 15; border.color: "#666"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 32; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.snoozeAlarm() }
                }
                Button {
                    text: "DISMISS"
                    Layout.preferredWidth: 260; Layout.preferredHeight: 100
                    background: Rectangle { color: "#CC0000"; radius: 15; border.color: "#FF5555"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 32; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.stopAlarm() }
                }
            }
        }
    }

    // --- TIME & DAY PICKER ---
    Popup {
        id: timePickerPopup
        width: 700
        height: 500
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#222"; radius: 25; border.color: "#555"; border.width: 2 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 35
            spacing: 20

            Text {
                text: editingAlarmId !== null ? "Edit Alarm" : "New Alarm"
                color: "white"; font.pixelSize: 36; font.bold: true; Layout.alignment: Qt.AlignHCenter
            }

            // Time Wheels
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 20
                Tumbler {
                    id: hoursTumbler
                    model: 24
                    visibleItemCount: 3
                    delegate: Text { text: String(modelData).padStart(2, '0'); color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; font.pixelSize: Tumbler.displacement === 0 ? 80 : 50; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 }
                }
                Text { text: ":"; color: "white"; font.pixelSize: 80; font.bold: true }
                Tumbler {
                    id: minutesTumbler
                    model: 60
                    visibleItemCount: 3
                    delegate: Text { text: String(modelData).padStart(2, '0'); color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; font.pixelSize: Tumbler.displacement === 0 ? 80 : 50; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 }
                }
            }

            // Day Selector
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 15
                Repeater {
                    id: dayRepeater
                    model: ["M", "T", "W", "T", "F", "S", "S"]
                    Button {
                        property bool isSelected: false
                        implicitWidth: 60; implicitHeight: 60
                        background: Rectangle { color: isSelected ? "#4facfe" : "#333"; radius: 30; border.color: isSelected ? "white" : "#555" }
                        contentItem: Text { text: modelData; color: isSelected ? "white" : "#AAA"; font.pixelSize: 24; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { isSelected = !isSelected }
                    }
                }
            }

            Button {
                text: "Save Alarm"
                Layout.fillWidth: true; Layout.preferredHeight: 70
                background: Rectangle { color: "#4facfe"; radius: 12 }
                contentItem: Text { text: "Save"; color: "white"; font.pixelSize: 26; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: {
                    var h = String(hoursTumbler.currentIndex).padStart(2, '0')
                    var m = String(minutesTumbler.currentIndex).padStart(2, '0')
                    var timeStr = h + ":" + m
                    var selectedDays = []
                    for(var i=0; i < dayRepeater.count; i++) { if(dayRepeater.itemAt(i).isSelected) selectedDays.push(i) }
                    var daysStr = selectedDays.join(",")
                    if(daysStr === "") daysStr = "Daily"

                    if (editingAlarmId !== null) { backend.updateAlarm(editingAlarmId, timeStr, daysStr) }
                    else { backend.createAlarm(timeStr, daysStr) }
                    timePickerPopup.close()
                }
            }
        }
    }

    // --- MAIN INTERFACE ---
    SwipeView {
        id: swipeView
        anchors.fill: parent
        currentIndex: 0 

        // SCREEN 1: THE CLOCK
        Item {
            Rectangle {
                id: clockBox
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 30
                anchors.bottomMargin: 45 

                // Dynamic width based on text
                width: clockLayout.width + 60 
                height: clockLayout.height + 40
                
                // Remove background/border at night
                color: backend.isNightMode ? "transparent" : "#AA000000"
                radius: 25
                border.color: backend.isNightMode ? "transparent" : "#33FFFFFF"
                border.width: 1
                
                Behavior on color { ColorAnimation { duration: 500 } }

                ColumnLayout {
                    id: clockLayout
                    anchors.centerIn: parent
                    spacing: -5
                    
                    Text {
                        text: backend.currentTime
                        // Red at night, White at day
                        color: backend.isNightMode ? "#FF3333" : "white"
                        
                        font.pixelSize: 90 // UPDATED TO 90
                        font.bold: true
                        style: Text.Outline
                        styleColor: "black"
                        Layout.alignment: Qt.AlignLeft
                        
                        Behavior on color { ColorAnimation { duration: 500 } }
                    }
                    
                    Text {
                        text: Qt.formatDate(new Date(), "dddd, MMMM d")
                        color: backend.isNightMode ? "#990000" : "#EEEEEE"
                        
                        font.pixelSize: 20 // UPDATED TO 20
                        font.weight: Font.DemiBold
                        Layout.alignment: Qt.AlignLeft
                        
                        Behavior on color { ColorAnimation { duration: 500 } }
                    }
                }
            }
        }

        // SCREEN 2: ALARM LIST
        Item {
            ListView {
                id: alarmListView
                anchors.fill: parent; anchors.margins: 30
                clip: true; spacing: 20
                model: backend.alarmList

                header: Text { text: "Your Alarms"; color: "white"; font.pixelSize: 42; font.bold: true; bottomPadding: 20 }
                
                delegate: Rectangle {
                    width: alarmListView.width
                    height: 120
                    color: "#CC222222"
                    radius: 20
                    border.color: modelData.active ? "#4facfe" : "#555"
                    border.width: 2

                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 35; anchors.rightMargin: 35
                        
                        ColumnLayout {
                            Layout.alignment: Qt.AlignVCenter; spacing: 4
                            Text { 
                                text: modelData.time
                                color: modelData.active ? "white" : "#666"
                                font.pixelSize: 54; font.bold: true
                            }
                            Text { 
                                property var dayMap: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                                text: {
                                    if (modelData.days === "Daily") return "Every Day"
                                    var idxs = modelData.days.split(",")
                                    if (idxs.length === 7) return "Every Day"
                                    var labels = []
                                    for(var i=0; i<idxs.length; i++) labels.push(dayMap[parseInt(idxs[i])])
                                    return labels.join(", ")
                                }
                                color: modelData.active ? "#BBBBBB" : "#444"
                                font.pixelSize: 20; font.weight: Font.Medium
                            }
                        }
                        
                        Item { Layout.fillWidth: true } 

                        Switch {
                            id: alarmSwitch
                            Layout.preferredWidth: 80
                            Layout.preferredHeight: 40
                            checked: modelData.active === 1
                            onToggled: backend.toggleAlarm(modelData.id, checked)

                            indicator: Item {
                                implicitWidth: 80
                                implicitHeight: 40
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 20
                                    color: alarmSwitch.checked ? "#4facfe" : "#333"
                                    border.color: alarmSwitch.checked ? "#4facfe" : "#555"
                                    border.width: 1
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                    Behavior on border.color { ColorAnimation { duration: 200 } }
                                }
                                Rectangle {
                                    x: alarmSwitch.checked ? parent.width - width - 6 : 6
                                    y: 6
                                    width: 28; height: 28; radius: 14; color: "white"
                                    Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.InOutQuad } }
                                }
                            }
                        }

                        Rectangle { width: 1; height: 50; color: "#444"; Layout.margins: 20 }

                        Button {
                            text: "✎"
                            Layout.preferredWidth: 50; Layout.preferredHeight: 50
                            background: Rectangle { color: "transparent" }
                            contentItem: Text { text: "✎"; color: "white"; font.pixelSize: 32; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: {
                                editingAlarmId = modelData.id
                                var parts = modelData.time.split(":")
                                hoursTumbler.currentIndex = parseInt(parts[0])
                                minutesTumbler.currentIndex = parseInt(parts[1])
                                var activeDays = modelData.days.split(",")
                                for(var i=0; i < dayRepeater.count; i++) {
                                    dayRepeater.itemAt(i).isSelected = (modelData.days === "Daily" || activeDays.indexOf(String(i)) !== -1)
                                }
                                timePickerPopup.open()
                            }
                        }

                        Button {
                            text: "✕"
                            Layout.preferredWidth: 50; Layout.preferredHeight: 50
                            background: Rectangle { color: "transparent" }
                            contentItem: Text { text: "✕"; color: "#FF4444"; font.pixelSize: 36; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: backend.deleteAlarm(modelData.id)
                        }
                    }
                }
            }

            Button {
                width: 100; height: 100
                anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 40
                background: Rectangle { color: "#4facfe"; radius: 50; border.color: "white"; border.width: 2; layer.enabled: true }
                contentItem: Text { text: "+"; color: "white"; font.pixelSize: 55; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: {
                    editingAlarmId = null 
                    var now = new Date()
                    hoursTumbler.currentIndex = now.getHours()
                    minutesTumbler.currentIndex = now.getMinutes()
                    for(var i=0; i < dayRepeater.count; i++) dayRepeater.itemAt(i).isSelected = false
                    timePickerPopup.open()
                }
            }
        }
    }
    
    PageIndicator {
        count: swipeView.count; currentIndex: swipeView.currentIndex
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 20
        spacing: 15
        delegate: Rectangle { width: 16; height: 16; radius: 8; color: index === swipeView.currentIndex ? "white" : "#66ffffff" }
    }
}