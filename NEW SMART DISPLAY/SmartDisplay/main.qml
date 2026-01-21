import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    visible: true
    visibility: Window.FullScreen // Kiosk mode
    // width: 1024 // Uncomment for desktop testing
    // height: 600
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
        
        // Global light overlay (for clock visibility)
        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: 0.2
        }
    }

    // --- ALARM TRIGGERED POPUP ---
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

    // --- ALARM EDIT/CREATE POPUP ---
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
            
            // Time Wheels (Corrected Font Sizes)
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
                        font.pixelSize: Tumbler.displacement === 0 ? 60 : 40; // FIX: Smaller text
                        font.bold: true; 
                        horizontalAlignment: Text.AlignHCenter; 
                        verticalAlignment: Text.AlignVCenter; 
                        opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 
                    }
                }
                Text { 
                    text: ":"; 
                    color: "white"; 
                    font.pixelSize: 60; // FIX: Smaller separator
                    font.bold: true 
                }
                Tumbler {
                    id: minutesTumbler
                    model: 60
                    visibleItemCount: 3
                    delegate: Text { 
                        text: String(modelData).padStart(2, '0'); 
                        color: Tumbler.displacement === 0 ? "#4facfe" : "#666"; 
                        font.pixelSize: Tumbler.displacement === 0 ? 60 : 40; // FIX: Smaller text
                        font.bold: true; 
                        horizontalAlignment: Text.AlignHCenter; 
                        verticalAlignment: Text.AlignVCenter; 
                        opacity: 1.0 - Math.abs(Tumbler.displacement) / 2.0 
                    }
                }
            }

            // Days Selection
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

    // --- DAY EVENT DETAILS POPUP (FULL DETAILS) ---
    Popup {
        id: dayDetailsPopup
        width: 700
        height: 550
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: "#1E1E1E"; radius: 25; border.color: "#4facfe"; border.width: 2 }
        
        property date selectedDate: new Date()
        property var eventsForDay: []

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 25
            spacing: 15
            
            Text {
                text: Qt.formatDate(dayDetailsPopup.selectedDate, "dddd, MMMM d")
                color: "white"
                font.pixelSize: 32
                font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            
            Rectangle { Layout.fillWidth: true; height: 1; color: "#444" }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: dayDetailsPopup.eventsForDay
                spacing: 15
                
                delegate: Rectangle {
                    width: parent.width
                    height: detailsCol.implicitHeight + 30 
                    color: "#333"
                    radius: 10
                    
                    ColumnLayout {
                        id: detailsCol
                        anchors.fill: parent
                        anchors.margins: 15
                        spacing: 5

                        // Title & Time
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 15
                            
                            Rectangle {
                                color: "#4facfe"
                                width: timeText.implicitWidth + 20
                                height: 30
                                radius: 15
                                Text {
                                    id: timeText
                                    anchors.centerIn: parent
                                    text: modelData.date.includes(",") ? modelData.date.split(",")[1].trim() : modelData.date
                                    color: "white"
                                    font.bold: true
                                    font.pixelSize: 16
                                }
                            }

                            Text { 
                                text: modelData.title
                                color: "white"
                                font.pixelSize: 22
                                font.bold: true
                                Layout.fillWidth: true
                                wrapMode: Text.Wrap
                            }
                        }

                        // Location
                        RowLayout {
                            visible: modelData.location !== ""
                            Layout.fillWidth: true
                            Text {
                                text: "📍 " + modelData.location
                                color: "#AAAAAA"
                                font.pixelSize: 18
                                font.italic: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                        }

                        // Description
                        Text {
                            visible: modelData.description !== ""
                            text: modelData.description
                            color: "#CCCCCC"
                            font.pixelSize: 16
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            Layout.topMargin: 5
                        }
                    }
                }
                
                Text {
                    visible: dayDetailsPopup.eventsForDay.length === 0
                    text: "No events scheduled"
                    color: "#666"
                    font.pixelSize: 20
                    anchors.centerIn: parent
                }
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

    // --- MAIN INTERFACE ---
    SwipeView {
        id: swipeView
        anchors.fill: parent
        currentIndex: 1 // Default to center page (optional, usually 0 is clock)

        // PAGE 1: ALARMS (with Dark Background)
        Item {
            // Dark Background Rectangle for Readability
            Rectangle {
                anchors.fill: parent
                color: "#CC000000" // 80% opacity black
            }

            ListView {
                id: alarmListView
                anchors.fill: parent; anchors.margins: 30
                clip: true; spacing: 20
                model: backend.alarmList

                header: Text { text: "Your Alarms"; color: "white"; font.pixelSize: 42; font.bold: true; bottomPadding: 20 }
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
                            onToggled: backend.toggleAlarm(modelData.id, checked)
                            indicator: Item {
                                implicitWidth: 80; implicitHeight: 40
                                Rectangle {
                                    anchors.fill: parent; radius: 20
                                    color: alarmSwitch.checked ? "#4facfe" : "#333"
                                    border.color: alarmSwitch.checked ? "#4facfe" : "#555"; border.width: 1
                                    Behavior on color { ColorAnimation { duration: 200 } }
                                }
                                Rectangle {
                                    x: alarmSwitch.checked ? parent.width - width - 6 : 6; y: 6
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
                            contentItem: Text { text: "✕"; color: "white"; font.pixelSize: 32; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
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
        
        // PAGE 2: CLOCK
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
                    spacing: -5
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
                        font.pixelSize: 20
                        font.weight: Font.DemiBold
                        Layout.alignment: Qt.AlignLeft
                        Behavior on color { ColorAnimation { duration: 500 } }
                    }
                }
            }
        }
        
        // PAGE 3: CALENDAR GRID (with Dark Background)
        Item {
            id: calendarPage
            
            // Dark Background for Readability
            Rectangle {
                anchors.fill: parent
                color: "#CC000000"
            }
            
            property date viewDate: new Date()
            
            function daysInMonth(anyDateInMonth) {
                return new Date(anyDateInMonth.getFullYear(), anyDateInMonth.getMonth() + 1, 0).getDate();
            }
            
            function firstDayOffset(anyDateInMonth) {
                var d = new Date(anyDateInMonth.getFullYear(), anyDateInMonth.getMonth(), 1);
                var day = d.getDay(); 
                return day === 0 ? 6 : day - 1; 
            }

            function getCellDate(index) {
                var firstDay = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1);
                var offset = firstDayOffset(firstDay);
                return new Date(viewDate.getFullYear(), viewDate.getMonth(), 1 + (index - offset));
            }

            function getEventsForDate(dateObj) {
                var dayEvents = []
                if (!backend.calendarEvents) return dayEvents 
                var checkStr = Qt.formatDate(dateObj, "yyyy-MM-dd")
                
                for(var i=0; i<backend.calendarEvents.length; i++) {
                     var evIso = backend.calendarEvents[i].date_iso
                     if (evIso.substring(0, 10) === checkStr) {
                         dayEvents.push(backend.calendarEvents[i])
                     }
                }
                return dayEvents
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 10

                // Month Header
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    Item { Layout.fillWidth: true } 
                    Button {
                        text: "◀"
                        background: Rectangle { color: "#333"; radius: 5 }
                        contentItem: Text { text: "◀"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: calendarPage.viewDate = new Date(calendarPage.viewDate.getFullYear(), calendarPage.viewDate.getMonth() - 1, 1)
                    }
                    Text {
                        text: Qt.formatDate(calendarPage.viewDate, "MMMM yyyy")
                        color: "white"
                        font.pixelSize: 32
                        font.bold: true
                    }
                    Button {
                        text: "▶"
                        background: Rectangle { color: "#333"; radius: 5 }
                        contentItem: Text { text: "▶"; color: "white"; font.pixelSize: 20; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        onClicked: calendarPage.viewDate = new Date(calendarPage.viewDate.getFullYear(), calendarPage.viewDate.getMonth() + 1, 1)
                    }
                    Item { Layout.fillWidth: true } 
                }

                // Days Header (Mon-Sun)
                RowLayout {
                    Layout.fillWidth: true
                    Repeater {
                        model: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                        Text {
                            text: modelData
                            color: "#888"
                            font.bold: true
                            font.pixelSize: 18
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }

                // Calendar Grid with Brief Details
                GridLayout {
                    columns: 7
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columnSpacing: 5
                    rowSpacing: 5

                    Repeater {
                        model: 42 
                        
                        Rectangle {
                            property date myDate: calendarPage.getCellDate(index)
                            property bool isCurrentMonth: myDate.getMonth() === calendarPage.viewDate.getMonth()
                            property bool isToday: Qt.formatDate(myDate, "yyyy-MM-dd") === Qt.formatDate(new Date(), "yyyy-MM-dd")
                            property var myEvents: calendarPage.getEventsForDate(myDate)
                            
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: isToday ? "#334facfe" : (isCurrentMonth ? "#22FFFFFF" : "transparent") 
                            radius: 5
                            border.color: isToday ? "#4facfe" : "transparent"
                            border.width: 1
                            clip: true 

                            // Day Number (Top Left)
                            Text {
                                text: myDate.getDate()
                                color: isCurrentMonth ? "white" : "#444"
                                font.pixelSize: 18
                                font.bold: isToday
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.margins: 5
                            }

                            // Brief Event List
                            Column {
                                anchors.top: parent.top
                                anchors.topMargin: 30 
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 2
                                spacing: 2
                                visible: isCurrentMonth

                                Repeater {
                                    model: myEvents.length > 3 ? myEvents.slice(0, 3) : myEvents
                                    
                                    Rectangle {
                                        height: 12  
                                        width: parent.width
                                        color: "#4facfe"
                                        radius: 6
                                        
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 5
                                            anchors.rightMargin: 5
                                            spacing: 4

                                            // Time
                                            Text {
                                                text: Qt.formatTime(new Date(modelData.date_iso), "hh:mm")
                                                color: "#DAEFFF" 
                                                font.pixelSize: 10
                                                font.weight: Font.Normal
                                            }

                                            // Title
                                            Text {
                                                text: modelData.title
                                                color: "white"
                                                font.pixelSize: 10
                                                font.bold: true
                                                Layout.fillWidth: true
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                                
                                // Show "+" if more events exist
                                Text {
                                    visible: myEvents.length > 3
                                    text: "+" + (myEvents.length - 3) + " more"
                                    color: "#888"
                                    font.pixelSize: 10
                                    anchors.horizontalCenter: parent.horizontalCenter
                                }
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
    }
    
    PageIndicator {
        count: swipeView.count; currentIndex: swipeView.currentIndex
        anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 20
        spacing: 15
        delegate: Rectangle { width: 16; height: 16; radius: 8; color: index === swipeView.currentIndex ? "white" : "#66ffffff" }
    }
}