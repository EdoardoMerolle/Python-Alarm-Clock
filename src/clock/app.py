from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from datetime import datetime


class AlarmClockApp(App):
    def build(self):
        self.label = Label(font_size=64)
        Clock.schedule_interval(self.update_time, 1)
        self.update_time(0)
        return self.label

    def update_time(self, _):
        self.label.text = datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    AlarmClockApp().run()
