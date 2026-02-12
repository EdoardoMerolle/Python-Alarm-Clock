import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    visibility: Window.FullScreen // Kiosk mode
    title: "Smart Display"
    color: "#000000"

    property var editingAlarmId: null

    Connections {
        target: backend
        function onAlarmTriggered(message) { alarmPopup.open() }
    }

    // --- SLIDESHOW ---
    Item {
        id: slideshow
        anchors.fill: parent
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
                if (slideshow.showBg1) bg2.source = nextSource
                else bg1.source = nextSource
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

    // --- ALARM POPUP ---
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
                    text: "DISMISS"
                    Layout.preferredWidth: 260; Layout.preferredHeight: 100
                    background: Rectangle { color: "#CC0000"; radius: 15; border.color: "#FF5555"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 32; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.stopAlarm() }
                }
                Button {
                    text: "SNOOZE"
                    Layout.preferredWidth: 260; Layout.preferredHeight: 100
                    background: Rectangle { color: "#444444"; radius: 15; border.color: "#666"; border.width: 2 }
                    contentItem: Text { text: parent.text; color: "white"; font.pixelSize: 32; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    onClicked: { alarmPopup.close(); backend.snoozeAlarm() }
                }
            }
        }
    }

    // --- TIME PICKER ---
    Popup {
        id: timePickerPopup
        width: 700; height: 500
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#222"; radius: 25; border.color: "#555"; border.width: 2 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 35
            spacing: 20
            Text { text: editingAlarmId !== null ? "Edit Alarm" : "New Alarm"; color: "white"; font.pixelSize: 36; font.bold: true; Layout.alignment: Qt.AlignHCenter }
            
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 20
                Tumbler {
                    id: hoursTumbler
                    model: 24
                    visibleItemCount: 3
                    delegate: Text { 
                        text: String(modelData).padStart(2, '0'); 
                        color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; 
                        font.pixelSize: Tumbler.displacement === 0 ? 40 : 25; 
                        font.bold: true; 
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; 
                        opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 
                    }
                }
                Text { text: ":"; color: "white"; font.pixelSize: 40; font.bold: true }
                Tumbler {
                    id: minutesTumbler
                    model: 60
                    visibleItemCount: 3
                    delegate: Text { 
                        text: String(modelData).padStart(2, '0'); 
                        color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; 
                        font.pixelSize: Tumbler.displacement === 0 ? 40 : 25; 
                        font.bold: true; 
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; 
                        opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 
                    }
                }
            }

            RowLayout {
                Layout.alignment: Qt.AlignHCenter; spacing: 15
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

    // --- DETAILS POPUP ---
    Popup {
        id: dayDetailsPopup
        width: 700; height: 550
        anchors.centerIn: parent
        modal: true; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#1E1E1E"; radius: 25; border.color: "#4facfe"; border.width: 2 }
        
        property date selectedDate: new Date()
        property var eventsForDay: []

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 25; spacing: 15
            Text {
                text: Qt.formatDate(dayDetailsPopup.selectedDate, "dddd, MMMM d")
                color: "white"; font.pixelSize: 32; font.bold: true; Layout.alignment: Qt.AlignHCenter
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#444" }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                model: dayDetailsPopup.eventsForDay; spacing: 15
                delegate: Rectangle {
                    width: parent.width; height: detailsCol.implicitHeight + 30 
                    color: "#333"; radius: 10
                    ColumnLayout {
                        id: detailsCol
                        anchors.fill: parent; anchors.margins: 15; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true; spacing: 15
                            Rectangle {
                                color: "#4facfe"; width: timeText.implicitWidth + 20; height: 30; radius: 15
                                Text { id: timeText; anchors.centerIn: parent; text: modelData.date.includes(",") ? modelData.date.split(",")[1].trim() : modelData.date; color: "white"; font.bold: true; font.pixelSize: 16 }
                            }
                            Text { text: modelData.title; color: "white"; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
                        }
                        RowLayout {
                            visible: modelData.location !== ""
                            Layout.fillWidth: true
                            Text { text: "📍 " + modelData.location; color: "#AAAAAA"; font.pixelSize: 18; font.italic: true; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Text { visible: modelData.description !== ""; text: modelData.description; color: "#CCCCCC"; font.pixelSize: 16; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.topMargin: 5 }
                    }
                }
                Text { visible: dayDetailsPopup.eventsForDay.length === 0; text: "No events scheduled"; color: "#666"; font.pixelSize: 20; anchors.centerIn: parent }
            }
            Button {
                text: "Close"
                Layout.fillWidth: true; Layout.preferredHeight: 50
                background: Rectangle { color: "#333"; radius: 10 }
                contentItem: Text { text: "Close"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: dayDetailsPopup.close()
            }
        }
    }

    Popup {
        id: spotifyDevicesPopup
        width: 520
        height: 420
        anchors.centerIn: parent
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#1B1B1B"; radius: 20; border.color: "#3DDC97"; border.width: 2 }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            Text {
                text: "Spotify Devices"
                color: "white"
                font.pixelSize: 30
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 10
                model: backend.spotifyDevices

                delegate: Button {
                    width: parent.width
                    height: 68
                    background: Rectangle {
                        color: modelData.is_active ? "#2A3A2F" : "#252525"
                        radius: 12
                        border.color: modelData.is_active ? "#3DDC97" : "#3A3A3A"
                        border.width: 1
                    }
                    contentItem: RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 15
                        anchors.rightMargin: 15
                        spacing: 8
                        Text { text: modelData.name; color: "white"; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: modelData.type; color: "#A8A8A8"; font.pixelSize: 15 }
                    }
                    onClicked: {
                        backend.spotifySetDevice(modelData.id)
                        spotifyDevicesPopup.close()
                    }
                }
            }

            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 50
                background: Rectangle { color: "#2A2A2A"; radius: 10 }
                contentItem: Text { text: "Close"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: spotifyDevicesPopup.close()
            }
        }
    }

    // --- MAIN INTERFACE ---
    SwipeView {
        id: swipeView
        anchors.fill: parent
        currentIndex: 1 

        // PAGE 1: ALARMS
        Item {
            Rectangle { anchors.fill: parent; color: "#CC000000" }
            ListView {
                id: alarmListView
                anchors.fill: parent; anchors.margins: 30; clip: true; spacing: 20
                model: backend.alarmList
                property real preservedContentY: 0
                property bool restoreAfterModelUpdate: false
                header: Text { text: "Your Alarms"; color: "white"; font.pixelSize: 42; font.bold: true; bottomPadding: 20 }
                onModelChanged: {
                    if (restoreAfterModelUpdate) {
                        var maxY = Math.max(0, contentHeight - height)
                        contentY = Math.max(0, Math.min(preservedContentY, maxY))
                        restoreAfterModelUpdate = false
                    }
                }
                delegate: Rectangle {
                    width: alarmListView.width; height: 120
                    color: "#CC222222"; radius: 20
                    border.color: modelData.active ? "#4facfe" : "#555"; border.width: 2
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 35; anchors.rightMargin: 35
                        ColumnLayout {
                            Layout.alignment: Qt.AlignVCenter; spacing: 4
                            Text { text: modelData.time; color: modelData.active ? "white" : "#666"; font.pixelSize: 54; font.bold: true }
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
                                color: modelData.active ? "#BBBBBB" : "#444"; font.pixelSize: 20; font.weight: Font.Medium
                            }
                        }
                        Item { Layout.fillWidth: true } 
                        Switch {
                            id: alarmSwitch
                            Layout.preferredWidth: 80; Layout.preferredHeight: 40
                            checked: modelData.active === 1
                            onToggled: {
                                alarmListView.preservedContentY = alarmListView.contentY
                                alarmListView.restoreAfterModelUpdate = true
                                backend.toggleAlarm(modelData.id, checked)
                            }
                            indicator: Item {
                                implicitWidth: 80; implicitHeight: 40
                                Rectangle { anchors.fill: parent; radius: 20; color: alarmSwitch.checked ? "#4facfe" : "#333"; border.color: alarmSwitch.checked ? "#4facfe" : "#555"; border.width: 1; Behavior on color { ColorAnimation { duration: 200 } } }
                                Rectangle { x: alarmSwitch.checked ? parent.width - width - 6 : 6; y: 6; width: 28; height: 28; radius: 14; color: "white"; Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.InOutQuad } } }
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
                            contentItem: Text { text: "✕"; color: "white"; font.pixelSize: 32; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            onClicked: {
                                alarmListView.preservedContentY = alarmListView.contentY
                                alarmListView.restoreAfterModelUpdate = true
                                backend.deleteAlarm(modelData.id)
                            }
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
        
        // PAGE 2: CLOCK & WEATHER
        Item {
            Rectangle {
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.margins: 30
                anchors.bottomMargin: 60 
                width: clockLayout.width + 60 
                height: clockLayout.height + 40
                color: backend.isNightMode ? "transparent" : "#AA000000"
                radius: 25
                border.color: backend.isNightMode ? "transparent" : "#33FFFFFF"
                border.width: 1
                Behavior on color { ColorAnimation { duration: 500 } }

                ColumnLayout {
                    id: clockLayout
                    anchors.centerIn: parent
                    spacing: 5 // Added space for weather

                    // WEATHER ROW
                    RowLayout {
                        Layout.alignment: Qt.AlignLeft
                        spacing: 15
                        visible: !backend.isNightMode && backend.weatherTemp !== "--"

                        Image {
                            source: backend.weatherIcon
                            Layout.preferredWidth: 40
                            Layout.preferredHeight: 40
                            fillMode: Image.PreserveAspectFit
                        }
                        
                        Text {
                            text: backend.weatherTemp
                            color: "white"
                            font.pixelSize: 28
                            font.bold: true
                        }
                        
                        Text {
                            text: backend.weatherDesc
                            color: "#DDDDDD"
                            font.pixelSize: 20
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }

                    Text {
                        text: backend.currentTime
                        color: backend.isNightMode ? "#FF3333" : "white"
                        font.pixelSize: 90
                        font.bold: true
                        style: Text.Outline; styleColor: "black"
                        Layout.alignment: Qt.AlignLeft
                        Behavior on color { ColorAnimation { duration: 500 } }
                    }
                    Text {
                        text: Qt.formatDate(new Date(), "dddd, MMMM d")
                        color: backend.isNightMode ? "#990000" : "#EEEEEE"
                        font.pixelSize: 22
                        font.weight: Font.DemiBold
                        Layout.alignment: Qt.AlignLeft
                        Behavior on color { ColorAnimation { duration: 500 } }
                    }
                    Text {
                        text: backend.snoozeStatus
                        visible: backend.snoozeStatus !== ""
                        color: backend.isNightMode ? "#FF8888" : "#FFD166"
                        font.pixelSize: 20
                        font.bold: true
                        Layout.alignment: Qt.AlignLeft
                    }
                }
            }
            
            // --- NEW: LIGHT TEST BUTTON (Top Left) ---
            Button {
                width: 50
                height: 50
                anchors.top: parent.top
                anchors.left: parent.left // Positioned top-left
                anchors.margins: 20

                background: Rectangle {
                    // Glows yellow when on, semi-transparent black when off
                    color: backend.lightIsOn ? "#CCFFCC00" : "#33000000"
                    radius: width / 2
                    border.color: backend.lightIsOn ? "#FFFF00" : "#33FFFFFF"
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 200 } }
                }

                contentItem: Text {
                    text: "💡"
                    color: "white"
                    font.pixelSize: 24
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    opacity: backend.lightIsOn ? 1.0 : 0.6
                }

                onClicked: backend.toggleLight()
            }

            // --- CLOSE BUTTON (Top Right) ---
            Button {
                width: 50; height: 50
                anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 20
                background: Rectangle { color: "#33000000"; radius: width / 2; border.color: "#33FFFFFF"; border.width: 1 }
                contentItem: Text { text: "✕"; color: "white"; font.pixelSize: 22; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: 0.6 }
                onClicked: Qt.quit()
            }
        }

        // PAGE 3: CALENDAR GRID
        Item {
            id: calendarPage
            Rectangle { anchors.fill: parent; color: "#CC000000" }
            property date viewDate: new Date()
            function daysInMonth(anyDateInMonth) { return new Date(anyDateInMonth.getFullYear(), anyDateInMonth.getMonth() + 1, 0).getDate(); }
            function firstDayOffset(anyDateInMonth) { var d = new Date(anyDateInMonth.getFullYear(), anyDateInMonth.getMonth(), 1); var day = d.getDay(); return day === 0 ? 6 : day - 1; }
            function getCellDate(index) { var firstDay = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1); var offset = firstDayOffset(firstDay); return new Date(viewDate.getFullYear(), viewDate.getMonth(), 1 + (index - offset)); }
            function getEventsForDate(dateObj) {
                var dayEvents = []
                if (!backend.calendarEvents) return dayEvents 
                var checkStr = Qt.formatDate(dateObj, "yyyy-MM-dd")
                for(var i=0; i<backend.calendarEvents.length; i++) {
                     var evIso = backend.calendarEvents[i].date_iso
                     if (evIso.substring(0, 10) === checkStr) { dayEvents.push(backend.calendarEvents[i]) }
                }
                return dayEvents
            }

            ColumnLayout {
                anchors.fill: parent; anchors.margins: 20; spacing: 10
                RowLayout {
                    Layout.fillWidth: true; spacing: 20
                    Item { Layout.fillWidth: true } 
                    Button {
                        text: "◀"; background: Rectangle { color: "#333"; radius: 5 }
                        contentItem: Text { text: "◀"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: calendarPage.viewDate = new Date(calendarPage.viewDate.getFullYear(), calendarPage.viewDate.getMonth() - 1, 1)
                    }
                    Text { text: Qt.formatDate(calendarPage.viewDate, "MMMM yyyy"); color: "white"; font.pixelSize: 32; font.bold: true }
                    Button {
                        text: "▶"; background: Rectangle { color: "#333"; radius: 5 }
                        contentItem: Text { text: "▶"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: calendarPage.viewDate = new Date(calendarPage.viewDate.getFullYear(), calendarPage.viewDate.getMonth() + 1, 1)
                    }
                    Item { Layout.fillWidth: true } 
                }
                RowLayout {
                    Layout.fillWidth: true
                    Repeater {
                        model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        Text { text: modelData; color: "#888"; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                    }
                }
                GridLayout {
                    columns: 7; Layout.fillWidth: true; Layout.fillHeight: true; columnSpacing: 5; rowSpacing: 5
                    Repeater {
                        model: 42 
                        Rectangle {
                            property date myDate: calendarPage.getCellDate(index)
                            property bool isCurrentMonth: myDate.getMonth() === calendarPage.viewDate.getMonth()
                            property bool isToday: Qt.formatDate(myDate, "yyyy-MM-dd") === Qt.formatDate(new Date(), "yyyy-MM-dd")
                            property var myEvents: calendarPage.getEventsForDate(myDate)
                            
                            Layout.fillWidth: true; Layout.fillHeight: true
                            color: isToday ? "#334facfe" : (isCurrentMonth ? "#22FFFFFF" : "transparent") 
                            radius: 5
                            border.color: isToday ? "#4facfe" : "transparent"; border.width: 1
                            clip: true 

                            Text {
                                text: myDate.getDate(); color: isCurrentMonth ? "white" : "#444"
                                font.pixelSize: 18; font.bold: isToday
                                anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 5
                            }
                            Column {
                                anchors.top: parent.top; anchors.topMargin: 30 
                                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 2; spacing: 2
                                visible: isCurrentMonth
                                Repeater {
                                    model: myEvents.length > 3 ? myEvents.slice(0, 3) : myEvents
                                    Rectangle {
                                        height: 12; width: parent.width; color: "#4facfe"; radius: 6
                                        RowLayout {
                                            anchors.fill: parent; anchors.leftMargin: 5; anchors.rightMargin: 5; spacing: 4
                                            Text { text: Qt.formatTime(new Date(modelData.date_iso), "hh:mm"); color: "#DAEFFF"; font.pixelSize: 10; font.weight: Font.Normal }
                                            Text { text: modelData.title; color: "white"; font.pixelSize: 10; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                        }
                                    }
                                }
                                Text { visible: myEvents.length > 3; text: "+" + (myEvents.length - 3) + " more"; color: "#888"; font.pixelSize: 10; anchors.horizontalCenter: parent.horizontalCenter }
                            }
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (myEvents.length > 0) {
                                        dayDetailsPopup.selectedDate = myDate
                                        dayDetailsPopup.eventsForDay = myEvents
                                        dayDetailsPopup.open()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // PAGE 4: SPOTIFY
        Item {
            id: spotifyPage
            property bool controlsVisible: false
            function revealControls() {
                controlsVisible = true
                controlsHideTimer.restart()
            }

            Timer {
                id: controlsHideTimer
                interval: 5000
                repeat: false
                onTriggered: spotifyPage.controlsVisible = false
            }

            Rectangle { anchors.fill: parent; color: "#10141B" }

            Image {
                anchors.fill: parent
                source: backend.spotifyAlbumArt
                fillMode: Image.PreserveAspectCrop
                visible: backend.spotifyAlbumArt !== ""
                opacity: 0.35
            }

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#6D1A202A" }
                    GradientStop { position: 0.52; color: "#8A12161E" }
                    GradientStop { position: 1.0; color: "#E2080A10" }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 24
                anchors.topMargin: 18
                width: Math.min(parent.width * 0.48, 460)
                height: 66
                radius: 3
                color: "#50000000"
                border.color: "#44FFFFFF"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10
                    Text {
                        text: "♪"
                        color: "#E5E5E5"
                        font.pixelSize: 20
                        font.bold: true
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            text: "PLAYING ON"
                            color: "#D0D0D0"
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 1.0
                        }
                        Text {
                            text: backend.spotifyDeviceName
                            color: "white"
                            font.pixelSize: 16
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.rightMargin: 24
                anchors.topMargin: 18
                width: Math.min(parent.width * 0.32, 300)
                height: 66
                radius: 3
                color: "#65000000"
                border.color: "#44FFFFFF"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 48
                        Layout.preferredHeight: 48
                        radius: 2
                        color: "#27313E"
                        clip: true
                        Image {
                            anchors.fill: parent
                            source: backend.spotifyAlbumArt
                            fillMode: Image.PreserveAspectCrop
                            visible: backend.spotifyAlbumArt !== ""
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Text {
                            text: "NOW PLAYING"
                            color: "#D8D8D8"
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 0.8
                        }
                        Text {
                            text: backend.spotifyTrack
                            color: "white"
                            font.pixelSize: 15
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            Rectangle {
                id: albumThumb
                width: 88
                height: 88
                radius: 4
                color: "#2B3340"
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.leftMargin: spotifyPage.controlsVisible ? 28 : 50
                anchors.bottomMargin: spotifyPage.controlsVisible ? 200 : 72
                clip: true
                z: 20
                Behavior on anchors.leftMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                Image {
                    anchors.fill: parent
                    source: backend.spotifyAlbumArt
                    fillMode: Image.PreserveAspectCrop
                    visible: backend.spotifyAlbumArt !== ""
                }
                Text {
                    anchors.centerIn: parent
                    text: "♪"
                    color: "#6A7A8B"
                    visible: backend.spotifyAlbumArt === ""
                    font.pixelSize: 46
                    font.bold: true
                }
            }

            Column {
                anchors.left: albumThumb.right
                anchors.right: parent.right
                anchors.rightMargin: 50
                anchors.bottom: parent.bottom
                anchors.leftMargin: 22
                anchors.bottomMargin: spotifyPage.controlsVisible ? 216 : 86
                spacing: 3
                z: 20
                Behavior on anchors.bottomMargin { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                Text {
                    text: backend.spotifyTrack
                    color: "white"
                    font.pixelSize: 54
                    font.bold: true
                    elide: Text.ElideRight
                    width: parent.width
                }
                Text {
                    text: backend.spotifyArtist
                    color: "#D4D8DE"
                    font.pixelSize: 20
                    font.bold: true
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            Rectangle {
                id: quickControls
                width: 290
                height: 86
                radius: 18
                color: "#A3151B24"
                border.color: "#4EA58A"
                border.width: 1
                x: (parent.width - width) / 2
                y: spotifyPage.controlsVisible ? (parent.height * 0.47) : (parent.height + 20)
                opacity: spotifyPage.controlsVisible ? 1.0 : 0.0
                z: 30
                Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: 180 } }

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 14
                    Button {
                        Layout.preferredWidth: 72
                        Layout.preferredHeight: 58
                        background: Rectangle { color: "#2A3340"; radius: 12; border.color: "#54708C"; border.width: 1 }
                        contentItem: Text { text: "PREV"; color: "#F4F7FB"; font.pixelSize: 18; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { spotifyPage.revealControls(); backend.spotifyPreviousTrack() }
                    }
                    Button {
                        Layout.preferredWidth: 96
                        Layout.preferredHeight: 58
                        background: Rectangle { color: "#46D89C"; radius: 12 }
                        contentItem: Text { text: backend.spotifyIsPlaying ? "PAUSE" : "PLAY"; color: "#0E1A15"; font.pixelSize: 18; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { spotifyPage.revealControls(); backend.spotifyTogglePlayPause() }
                    }
                    Button {
                        Layout.preferredWidth: 72
                        Layout.preferredHeight: 58
                        background: Rectangle { color: "#2A3340"; radius: 12; border.color: "#54708C"; border.width: 1 }
                        contentItem: Text { text: "NEXT"; color: "#F4F7FB"; font.pixelSize: 18; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { spotifyPage.revealControls(); backend.spotifyNextTrack() }
                    }
                }
            }

            Rectangle {
                id: optionsPanel
                width: Math.min(parent.width * 0.82, 860)
                height: 82
                radius: 14
                color: "#B00D121A"
                border.color: "#3AFFFFFF"
                border.width: 1
                x: (parent.width - width) / 2
                y: spotifyPage.controlsVisible ? (quickControls.y + quickControls.height + 14) : (parent.height + 20)
                opacity: spotifyPage.controlsVisible ? 1.0 : 0.0
                z: 29
                Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: 180 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 16
                    anchors.rightMargin: 16
                    spacing: 12

                    Button {
                        Layout.preferredWidth: 110
                        Layout.preferredHeight: 46
                        background: Rectangle { color: "#243F35"; radius: 10; border.color: "#4FAF83"; border.width: 1 }
                        contentItem: Text { text: "Devices"; color: "#AEEED0"; font.pixelSize: 15; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: { spotifyPage.revealControls(); backend.spotifyRefresh(); spotifyDevicesPopup.open() }
                    }
                    Button {
                        Layout.preferredWidth: 106
                        Layout.preferredHeight: 46
                        background: Rectangle {
                            color: backend.spotifyConnected ? "#2F343A" : "#3E2C20"
                            radius: 10
                            border.color: backend.spotifyConnected ? "#6A7179" : "#B0864D"
                            border.width: 1
                        }
                        contentItem: Text {
                            text: backend.spotifyConnected ? "Relink" : "Connect"
                            color: backend.spotifyConnected ? "#F2F2F2" : "#F4D4A1"
                            font.pixelSize: 15
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: { spotifyPage.revealControls(); backend.spotifyStartAuth() }
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: "Vol"
                        color: "#CFD8E4"
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Slider {
                        id: spotifyVolumeSlider
                        Layout.preferredWidth: Math.min(parent.width * 0.30, 300)
                        from: 0
                        to: 100
                        value: backend.spotifyVolume
                        onMoved: {
                            spotifyPage.revealControls()
                            backend.spotifySetVolume(Math.round(value))
                        }
                        background: Rectangle {
                            x: spotifyVolumeSlider.leftPadding
                            y: spotifyVolumeSlider.topPadding + spotifyVolumeSlider.availableHeight / 2 - height / 2
                            width: spotifyVolumeSlider.availableWidth
                            height: 6
                            radius: 3
                            color: "#334354"
                            Rectangle {
                                width: spotifyVolumeSlider.visualPosition * parent.width
                                height: parent.height
                                radius: 3
                                color: "#45D89A"
                            }
                        }
                        handle: Rectangle {
                            x: spotifyVolumeSlider.leftPadding + spotifyVolumeSlider.visualPosition * (spotifyVolumeSlider.availableWidth - width)
                            y: spotifyVolumeSlider.topPadding + spotifyVolumeSlider.availableHeight / 2 - height / 2
                            implicitWidth: 16
                            implicitHeight: 16
                            radius: 8
                            color: "#E9FCF2"
                            border.color: "#3EA276"
                            border.width: 1
                        }
                    }
                    Text {
                        text: Math.round(spotifyVolumeSlider.value) + "%"
                        color: "#CFD8E4"
                        font.pixelSize: 13
                        Layout.preferredWidth: 42
                        horizontalAlignment: Text.AlignRight
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                z: 10
                onPressed: {
                    spotifyPage.revealControls()
                    mouse.accepted = false
                }
            }
        }
    }
    
    PageIndicator {
        count: swipeView.count; currentIndex: swipeView.currentIndex
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 20
        spacing: 15
        delegate: Rectangle {
            width: 16; height: 16; radius: 8;
            color: index === swipeView.currentIndex ? (backend.isNightMode ? "#990000" : "white") : (backend.isNightMode ? "#33550000" : "#66ffffff") // Dim red for inactive at night
        }
    }

    // --- GLOBAL ACTIVITY DETECTOR (NEW) ---
    // This catches every click/tap to reset the inactivity timer
    MouseArea {
        anchors.fill: parent
        z: 99999 // Ensure it is on top of everything
        propagateComposedEvents: true // Allows clicks to pass through to underlying buttons
        onPressed: {
            backend.resetInactivityTimer()
            mouse.accepted = false // Pass the event down so buttons still work
        }
    }
}
