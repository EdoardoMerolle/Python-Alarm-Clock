import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    width: 800
    height: 480
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

        property var images: backend.imageList
        property int currentIndex: 0
        property bool showBg1: true 

        // Timer to change images
        Timer {
            interval: 10000 
            running: slideshow.images.length > 1 
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

        // Image 1
        Image {
            id: bg1
            anchors.fill: parent
            // FIX: Explicitly reference slideshow.images
            source: slideshow.images.length > 0 ? slideshow.images[0] : "" 
            fillMode: Image.PreserveAspectCrop
            opacity: slideshow.showBg1 ? 1.0 : 0.0 
            Behavior on opacity { NumberAnimation { duration: 2000 } } 
        }

        // Image 2
        Image {
            id: bg2
            anchors.fill: parent
            source: "" 
            fillMode: Image.PreserveAspectCrop
            opacity: slideshow.showBg1 ? 0.0 : 1.0 
            Behavior on opacity { NumberAnimation { duration: 2000 } }
        }

        // Dark Overlay
        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: 0.4
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
            spacing: 30
            Text { text: backend.currentTime; color: "white"; font.pixelSize: 100; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            Text { text: "WAKE UP"; color: "#FF4444"; font.pixelSize: 50; font.weight: Font.Black; Layout.alignment: Qt.AlignHCenter }
            RowLayout {
                spacing: 40
                Button {
                    text: "SNOOZE"
                    Layout.preferredWidth: 220; Layout.preferredHeight: 90
                    background: Rectangle { color: "#444444"; radius: 15; border.color: "#666"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 28; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.snoozeAlarm() }
                }
                Button {
                    text: "DISMISS"
                    Layout.preferredWidth: 220; Layout.preferredHeight: 90
                    background: Rectangle { color: "#CC0000"; radius: 15; border.color: "#FF5555"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 28; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.stopAlarm() }
                }
            }
        }
    }

    // --- TIME & DAY PICKER ---
    Popup {
        id: timePickerPopup
        width: 550
        height: 450
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#222"; radius: 25; border.color: "#555"; border.width: 2 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 25
            spacing: 15

            Text {
                text: editingAlarmId !== null ? "Edit Alarm" : "New Alarm"
                color: "white"; font.pixelSize: 28; font.bold: true; Layout.alignment: Qt.AlignHCenter
            }

            // Time Wheels
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 15
                Tumbler {
                    id: hoursTumbler
                    model: 24
                    visibleItemCount: 3
                    delegate: Text { text: String(modelData).padStart(2, '0'); color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; font.pixelSize: Tumbler.displacement === 0 ? 60 : 40; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 }
                }
                Text { text: ":"; color: "white"; font.pixelSize: 60; font.bold: true }
                Tumbler {
                    id: minutesTumbler
                    model: 60
                    visibleItemCount: 3
                    delegate: Text { text: String(modelData).padStart(2, '0'); color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; font.pixelSize: Tumbler.displacement === 0 ? 60 : 40; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 }
                }
            }

            // Day Selector
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 10
                Repeater {
                    id: dayRepeater
                    model: ["M", "T", "W", "T", "F", "S", "S"]
                    Button {
                        property bool isSelected: false
                        implicitWidth: 50; implicitHeight: 50
                        background: Rectangle { color: isSelected ? "#4facfe" : "#333"; radius: 25; border.color: isSelected ? "white" : "#555" }
                        contentItem: Text { text: modelData; color: isSelected ? "white" : "#AAA"; font.pixelSize: 20; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { isSelected = !isSelected }
                    }
                }
            }

            Button {
                text: "Save Alarm"
                Layout.fillWidth: true; Layout.preferredHeight: 60
                background: Rectangle { color: "#4facfe"; radius: 12 }
                contentItem: Text { text: "Save"; color: "white"; font.pixelSize: 22; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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

        // Screen 1: Clock
        Item {
            ColumnLayout {
                anchors.centerIn: parent; spacing: -5
                Text { text: backend.currentTime; color: "white"; font.pixelSize: 170; font.bold: true; style: Text.Outline; styleColor: "black"; Layout.alignment: Qt.AlignHCenter }
                Text { text: Qt.formatDate(new Date(), "dddd, MMMM d"); color: "#EEEEEE"; font.pixelSize: 28; font.weight: Font.DemiBold; Layout.alignment: Qt.AlignHCenter }
            }
        }

        // Screen 2: Alarm List
        Item {
            ListView {
                id: alarmListView
                anchors.fill: parent; anchors.margins: 20
                clip: true; spacing: 15
                model: backend.alarmList

                header: Text { text: "Your Alarms"; color: "white"; font.pixelSize: 36; font.bold: true; bottomPadding: 20 }
                
                delegate: Rectangle {
                    width: alarmListView.width
                    height: 100
                    color: "#CC222222"
                    radius: 15
                    border.color: modelData.active ? "#4facfe" : "#555"
                    border.width: 2

                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 25; anchors.rightMargin: 25
                        
                        // Text Info
                        ColumnLayout {
                            Layout.alignment: Qt.AlignVCenter; spacing: 2
                            Text { 
                                text: modelData.time
                                color: modelData.active ? "white" : "#666"
                                font.pixelSize: 42; font.bold: true 
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
                                font.pixelSize: 16; font.weight: Font.Medium
                            }
                        }
                        
                        // Spacer
                        Item { Layout.fillWidth: true } 

                        // Custom Toggle Switch
                        Switch {
                            id: alarmSwitch
                            Layout.preferredWidth: 60
                            Layout.preferredHeight: 32
                            checked: modelData.active === 1
                            onToggled: backend.toggleAlarm(modelData.id, checked)

                            indicator: Item {
                                implicitWidth: 60
                                implicitHeight: 32
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 16
                                    color: alarmSwitch.checked ? "#4facfe" : "#333"
                                    border.color: alarmSwitch.checked ? "#4facfe" : "#555"
                                    border.width: 1
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                    Behavior on border.color { ColorAnimation { duration: 200 } }
                                }
                                Rectangle {
                                    x: alarmSwitch.checked ? parent.width - width - 4 : 4
                                    y: 4
                                    width: 24; height: 24; radius: 12; color: "white"
                                    Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.InOutQuad } }
                                }
                            }
                        }

                        // Divider
                        Rectangle { width: 1; height: 40; color: "#444"; Layout.margins: 15 }

                        // Edit Button
                        Button {
                            text: "✎"
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 40
                            background: Rectangle { color: "transparent" }
                            contentItem: Text { text: "✎"; color: "white"; font.pixelSize: 24; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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

                        // Delete Button
                        Button {
                            text: "✕"
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 40
                            background: Rectangle { color: "transparent" }
                            contentItem: Text { text: "✕"; color: "#FF4444"; font.pixelSize: 28; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: backend.deleteAlarm(modelData.id)
                        }
                    }
                }
            }

            // ADD Button
            Button {
                width: 80; height: 80
                anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 30
                background: Rectangle { color: "#4facfe"; radius: 40; border.color: "white"; border.width: 2; layer.enabled: true }
                contentItem: Text { text: "+"; color: "white"; font.pixelSize: 45; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 15
        spacing: 12
        delegate: Rectangle { width: 12; height: 12; radius: 6; color: index === swipeView.currentIndex ? "white" : "#66ffffff" }
    }
}