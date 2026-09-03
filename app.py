from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen

# Schermata principale dell'app
class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Titolo o contenuto principale
        layout.add_widget(Label(text="Gestione Spesa", font_size='24sp', size_hint_y=0.2))
        
        # Area centrale (lista spesa o contenuti)
        layout.add_widget(Label(text="[Qui va la tua lista spesa]", size_hint_y=0.6))
        
        # Area Pulsanti in basso
        button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.2)
        
        # Tasto preesistente di esempio
        btn_lista = Button(text="La mia Lista")
        
        # NUOVO TASTO: Analisi e Statistiche
        btn_stats = Button(
            text="Analisi e Statistiche",
            background_color=(0.2, 0.6, 1, 1) # Un tocco di blu per evidenziarlo
        )
        # Collega il click al passaggio alla schermata delle statistiche
        btn_stats.bind(on_release=self.apri_statistiche)
        
        button_layout.add_widget(btn_lista)
        button_layout.add_widget(btn_stats)
        
        layout.add_widget(button_layout)
        self.add_widget(layout)

    def apri_statistiche(self, instance):
        # Cambia schermata verso la vista statistiche
        self.manager.current = 'stats_screen'

# Nuova schermata dedicata a grafici e metriche
class StatsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="Analisi & Statistiche di Spesa", font_size='22sp', size_hint_y=0.2))
        
        # Spazio per resoconto o grafici
        layout.add_widget(Label(text="• Totale Mese: 0.00 €\n• Categoria più acquistata: --", size_hint_y=0.6))
        
        btn_back = Button(text="Torna Indietro", size_hint_y=0.2)
        btn_back.bind(on_release=lambda x: setattr(self.manager, 'current', 'home_screen'))
        
        layout.add_widget(btn_back)
        self.add_widget(layout)

class SpesaApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home_screen'))
        sm.add_widget(StatsScreen(name='stats_screen'))
        return sm

if __name__ == '__main__':
    SpesaApp().run()
