import sys
import networkx as nx

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, Adw

from matplotlib.backends.backend_gtk4cairo import FigureCanvas
from matplotlib.figure import Figure

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fig = Figure(figsize=(6, 4), constrained_layout=True)
        self.fig.canvas.mpl_connect('button_press_event', self.choose_node)
        self.ax = self.fig.add_subplot()

        self.G = nx.Graph()
        
        self.english_letters = 'abcdefghijklmnopqrstuvwxyz1234567890'

        # [[Gtk.Box, Gtk.Entry_Name, Gtk.Entry_Weight, Gtk.ColorButton]]
        self.gui_edges = []

        self.build_main_window()
        self.redraw()

    def all_clear(self):
        self.entry_node_name.set_text('')
        self.entry_node_weight.set_text('')
        self.entry_node_desc.set_text('')
        self.box_edges_clear()
        self.set_color_to_button(self.button_color)

    def redraw(self, button=None):
        self.label_error.hide()
        self.ax.clear()
        self.pos = nx.nx_pydot.pydot_layout(self.G)

        xmas = []
        ymas = []
        if self.pos:
            for key in self.pos:
                x, y = self.pos[key]
                xmas.append(x)
                ymas.append(y)
                self.xr = max(xmas) - min(xmas)
                self.yr = max(ymas) - min(ymas)

        node_name_labels = {}
        node_color_map = []
        weight_labels = {}
        desc_labels = {}
        for node in self.G.nodes(data=True):
            node_name_labels.update({node[0]: node[0] + '\n\n\n\n'})

            try:
                hex_color = self.rgb2hex(node[1]['fillcolor'])
            except KeyError:
                hex_color = '#9a9996'
            finally:
                node_color_map.append(hex_color)

            try:
                desc = str(node[1]['description']).strip('"')
            except KeyError:
                pass
            else:
                if desc:
                    desc_labels.update({node[0]: desc}) 

            try:
                weight = str(node[1]['weight']).strip('"')
            except KeyError:
                pass
            else:
                if weight:
                    weight_labels.update({node[0]: '\n\n\n\n' + weight}) 

        edge_labels = {}
        edge_color_map = []
        for edge in self.G.edges(data=True):
            if 'weight' not in edge[2]:
                self.label_error.set_label('Ошибка в файле')
                self.label_error.show()
                return
            if 'fillcolor' in edge[2]:
                hex_color = self.rgb2hex(edge[2]['fillcolor'])
            else:
                hex_color = '#000000'
            edge_color_map.append(hex_color)
            edge_labels.update({(edge[0], edge[1]): str(edge[2]['weight'])})

        # Отрисовка обводки узлов
        nx.draw_networkx_nodes(
            self.G,
            self.pos,
            ax=self.ax,
            alpha=0.55,
            node_color='#000000',
            node_size=750
        )

        # Отрисовка узлов
        nx.draw_networkx_nodes(
            self.G,
            self.pos,
            ax=self.ax,
            node_color=node_color_map,
            node_size=600
        )

        # Отрисовка граней
        nx.draw_networkx_edges(
            self.G,
            self.pos,
            ax=self.ax,
            alpha=0.55,
            width=1.5,
            edge_color=edge_color_map
        )

        # Отрисовка имён узлов
        nx.draw_networkx_labels(
            self.G,
            self.pos,
            node_name_labels,
            ax=self.ax
        )

        # Отрисовка весов граней
        if self.switch_edges.get_active():
            nx.draw_networkx_edge_labels(
                self.G,
                self.pos,
                edge_labels=edge_labels,
                label_pos=self.w_scale.get_value() / 10,
                rotate=False,
                ax=self.ax
            )

        # Отрисовка весов узлов
        if self.switch_astar.get_active():
            nx.draw_networkx_labels(
                self.G,
                self.pos,
                weight_labels,
                ax=self.ax,
                font_color='#ff0000'
            )

        # Отрисовка подписей
        if self.switch_desc.get_active():
            nx.draw_networkx_labels(
                self.G,
                self.pos,
                desc_labels,
                ax=self.ax,
                font_color='#ffffff',
                bbox={'boxstyle': 'square', 'color': '#000000', 'alpha': 0.2}
            )

        self.fig.canvas.draw()

    def read_node(self, node_name, change=True):
        self.label_error.hide()
        if change:
            self.entry_node_name.set_text(node_name)

        if 'weight' in self.G.nodes[node_name]:
            self.entry_node_weight.set_text(str(self.G.nodes[node_name]['weight']))
        else:
            self.entry_node_weight.set_text('')

        if 'description' in self.G.nodes[node_name]:
            desc = str(self.G.nodes[node_name]['description'].strip('"'))
            if desc != '':
                self.entry_node_desc.set_text(desc)
            else:
                self.entry_node_desc.set_text('')
        else:
            self.entry_node_desc.set_text('')

        if 'fillcolor' in self.G.nodes[node_name]:
            hexcolor = self.rgb2hex(self.G.nodes[node_name]['fillcolor'])
            self.set_color_to_button(self.button_color, color_hex=hexcolor)
        else:
            self.set_color_to_button(self.button_color)
        
        self.box_edges_clear()
        for edge in self.G.edges(node_name, data=True):
            if 'fillcolor' not in edge[2]:
                color = 'rgb(0,0,0)'
            else:
                color = edge[2]['fillcolor']
            self.add_edge_field(node2=edge[1], weight=edge[2]['weight'], color=color)
        if self.switch_edges.get_active() is False:
            for _, _, entry2, _ in self.gui_edges:
                entry2.hide()

    def update_node(self, button=None):
        def is_good_name(name:str) -> bool:
            for let in name:
                if let.lower() not in self.english_letters:
                    return False
            return True
        node_name = self.entry_node_name.get_text()
        if node_name:
            if is_good_name(node_name) is False:
                self.entry_node_name.grab_focus()
                self.label_error.show()
                self.label_error.set_label('Неверное имя узла')
                return
        else:
            self.entry_node_name.grab_focus()
            self.label_error.show()
            self.label_error.set_label('Имя не может быть пустым')
            return

        node_weight = self.entry_node_weight.get_text()
        if self.switch_astar.get_active():
            if node_weight.isdigit() is False:
                self.entry_node_weight.grab_focus()
                self.label_error.set_label('Неправельное значение A*')
                self.label_error.show()
                return
        else:
            node_weight = 0

        fillcolor = self.button_color.get_rgba().to_string()

        description = self.entry_node_desc.get_text()

        self.G.add_node(node_name, weight=node_weight, fillcolor=fillcolor, description=description)

        edge_mas = []
        for _, entry_1, entry_2, button_color in self.gui_edges:
            node_name_second = entry_1.get_text().strip()
            edge_weight = entry_2.get_text().strip()
            color = button_color.get_rgba().to_string()

            if node_name_second:
                if is_good_name(node_name_second) is False:
                    entry_1.grab_focus()
                    self.label_error.show()
                    self.label_error.set_label('Неверное имя узла')
                    return
            else:
                entry_1.grab_focus()
                self.label_error.show()
                self.label_error.set_label('Имя не может быть пустым')
                return

            if self.switch_edges.get_active():
                if edge_weight:
                    try:
                        edge_weight = int(edge_weight)
                    except ValueError:
                        entry_2.grab_focus()
                        self.label_error.set_label('Вес должен быть числом')
                        self.label_error.show()
                        return
                else:
                    entry_2.grab_focus()
                    self.label_error.set_text(f'У грани ({node_name}, {node_name_second}) не указан вес')
                    self.label_error.show()
                    return
            else:
                edge_weight = 0
            edge_mas.append((node_name, node_name_second, edge_weight, color))

        edges = list(self.G.edges(node_name))
        self.G.remove_edges_from(edges)
        for node_name, node_name_second, edge_weight, color in edge_mas:
            self.G.add_edge(node_name, node_name_second, weight=edge_weight, fillcolor=color)

        self.redraw()

    def remove_node(self, button=None):
        node_name = self.entry_node_name.get_text().strip()
        if node_name in self.G.nodes:
            self.G.remove_node(node_name)
            self.all_clear()

            self.redraw()
        else:
            self.entry_node_name.grab_focus()
            self.label_error.show()
            self.label_error.set_label('Такого узла не существует')

    def choose_file(self, button, action):
        match action:
            case 'save_dot':
                ttitle = 'Save File (*.txt)'
                taction = Gtk.FileChooserAction.SAVE
                tbname ='Save (*.txt)'
            case 'open_dot':
                ttitle = 'Open File'
                taction = Gtk.FileChooserAction.OPEN
                tbname ='Open'
            case 'save_pic':
                ttitle = 'Save File (*.png)'
                taction = Gtk.FileChooserAction.SAVE
                tbname ='Save (*.png)'

        dialog = Gtk.FileChooserDialog(
            title=ttitle,
            action=taction,
            create_folders=True,
        )
        dialog.add_button(tbname, -10)
        dialog.connect('response', self.response, action)
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.show()

    def response(self, dialog, resp, action):
        if resp == -10:
            filename = dialog.get_file().get_path()
            match action:
                case 'save_dot':
                    self.save_dot(filename)
                case 'open_dot':
                    self.load_dot(filename)
                case 'save_pic':
                    self.save_pic(filename)
            dialog.destroy()

    def load_dot(self, filename:str):
        self.all_clear()
        self.G.clear()
        self.G = nx.nx_pydot.read_dot(filename)
        self.G.graph['graph'] = {'rankdir':'LR'}
        try:
            self.G.remove_node('\\n')
        except Exception:
            pass

        if self.G.is_directed():
            self.label_di.set_text('DiGraph')
            self.G = nx.DiGraph(self.G)
        else:
            self.label_di.set_text('Graph')
            self.G = nx.Graph(self.G)

        self.redraw()

    def save_pic(self, filename):
        if filename[-4:].lower() != '.png' or len(filename) == 3:
            filename += '.png'
        self.fig.savefig(filename)

    def save_dot(self, filename):
        if filename[-4:].lower() != '.txt' or len(filename) == 3:
            filename += '.txt'
        nx.nx_pydot.write_dot(self.G, filename)

    def rgb2hex(self, rgb:str):
        rgb = rgb.strip('"')
        if 'rgba' in rgb:
            colors = rgb[5:-1].split(',')
        else:
            colors = rgb[4:-1].split(',')
        colors = list(map(lambda c: hex(int(c)).lstrip('0x').zfill(2), colors))
        return f'#{colors[0]}{colors[1]}{colors[2]}'

    def choose_node(self, event):
        node_not_found = True
        for node in self.pos:
            posx, posy = self.pos[node]

            try:
                well_node_size = self.yr * 0.02
                if event.xdata > posx - well_node_size and event.xdata < posx + well_node_size and event.ydata > posy - well_node_size and event.ydata < posy + well_node_size:
                    self.read_node(node)
                    node_not_found = False
            except Exception:
                self.label_error.set_text('Это рамка :3')
                self.label_error.show()
        if node_not_found:
            self.all_clear()

    def switch_change_astar(self, widget, is_activated):
        if is_activated:
            self.entry_node_weight.show()
        else:
            self.entry_node_weight.hide()
        
        self.redraw()

    def switch_change_edges(self, widget, is_activated):
        if is_activated:
            self.w_scale.show()
            for _, _, entry2, _ in self.gui_edges:
                entry2.show()
        else:
            self.w_scale.hide()
            for _, _, entry2, _ in self.gui_edges:
                entry2.hide()
        
        self.redraw()

    def switch_change_desc(self, widget, is_activated):
        if is_activated:
            self.entry_node_desc.show()
        else:
            self.entry_node_desc.hide()
        
        self.redraw()

    def scale_changed(self, scale):
        self.slider_value = scale.get_value()
        
        self.redraw()
    
    def check_node(self, widget):
        node_name = self.entry_node_name.get_text()
        if node_name in self.G.nodes:
            self.read_node(node_name, change=False)

    def build_main_window(self):
        self.set_default_size(950, 600)
        self.set_title('UltraMegaSuperDuperHarosh')

        ## Основной box
        big_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL
        )
        self.set_child(big_box)

        ## Заголовок
        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)

        # Кнопка открытия файла DOT
        self.button_dot_load = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='document-open',
            tooltip_text='Открыть файл DOT'
        )
        self.button_dot_load.connect('clicked', self.choose_file, 'open_dot')
        self.header.pack_start(self.button_dot_load)

        # Кнопка сохранения в файл DOT
        self.button_dot_write = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='document-save',
            tooltip_text='Сохранить в файл DOT'
        )
        self.button_dot_write.connect('clicked', self.choose_file, 'save_dot')
        self.header.pack_start(self.button_dot_write)

        self.header.pack_start(Gtk.Separator())

        # Кнопка сохранения рабочей области в .png файл
        self.button_save = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='folder-picture',
            tooltip_text='Сохранить изображение рабочего пространства'
        )
        self.button_save.connect('clicked', self.choose_file, 'save_pic')
        self.header.pack_start(self.button_save)

        # Кнопка обновления рабочей области
        self.button_new = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='add',
            tooltip_text='Создать новый граф'
        )
        self.button_new.connect('clicked', self.pop_dialog)
        self.header.pack_start(self.button_new)

        self.label_di = Gtk.Label(
            label='Graph'
        )
        self.header.pack_start(self.label_di)

        # Здесь название окна

        # Отображение весов граней
        self.switch_edges = Gtk.Switch(
            active=False,
            tooltip_text='Переключение режима отображения веса граней'
        )
        self.switch_edges.connect('state-set', self.switch_change_edges)
        self.header.pack_end(self.switch_edges)
        self.header.pack_end(Gtk.Label(label='Ed'))

        self.header.pack_end(Gtk.Separator())

        # Отображение весов нод для A*
        self.switch_astar = Gtk.Switch(
            active=False,
            tooltip_text='Переключение режима отображения веса узлов'
        )
        self.switch_astar.connect('state-set', self.switch_change_astar)
        self.header.pack_end(self.switch_astar)
        self.header.pack_end(Gtk.Label(label=' A*'))

        self.header.pack_end(Gtk.Separator())

        # Отображение подписей
        self.switch_desc = Gtk.Switch(
            active=False,
            tooltip_text='Переключение отображения подписей'
        )
        self.switch_desc.connect('state-set', self.switch_change_desc)
        self.header.pack_end(self.switch_desc)
        self.header.pack_end(Gtk.Label(label='Desc'))

        self.header.pack_end(Gtk.Separator())

        # Скролл для расположения вестов граней
        self.w_scale = Gtk.Scale(
            draw_value=False,
            digits=1,
            adjustment=Gtk.Adjustment(
                value=5,
                lower=1.5,
                upper=8.5
            ),
            width_request=120,
            tooltip_text='Расположение значения веса на гранях'
        )
        self.w_scale.connect('value-changed', self.scale_changed)
        self.header.pack_end(self.w_scale)
        self.w_scale.hide()

        ## Панель для изображения
        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_size_request(400, 400)
        big_box.append(self.canvas)

        ## Правая панель
        self.right_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5,
            margin_start=5,
            margin_end=5,
            vexpand=True,
            hexpand=False,
            width_request=300
        )
        big_box.append(self.right_panel)

        # Имя узла
        self.right_panel.append(Gtk.Label(label='Выбранный узел'))
        box_node_name = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=5,
        )
        self.right_panel.append(box_node_name)
        
        self.entry_node_name = Gtk.Entry(
            placeholder_text='Имя узла',
            hexpand=True
        )

        self.entrycompletion = Gtk.EntryCompletion()


        self.entry_node_name.connect('activate', self.update_node)
        self.entry_node_name.connect('changed', self.check_node)
        box_node_name.append(self.entry_node_name)

        self.button_rm = Gtk.Button(
            width_request=47,
            height_request=32,
            icon_name='edit-delete',
            tooltip_text='Удалить выбранный узел'
        )
        self.button_rm.connect('clicked', self.remove_node)
        box_node_name.append(self.button_rm)

        self.right_panel.append(Gtk.Separator())

        ## Свойства узла
        self.right_panel.append(Gtk.Label(label='Свойства узла'))
        box_node_propertys = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=5,
        )
        self.right_panel.append(box_node_propertys)
        
        # A* штуковина
        self.entry_node_weight = Gtk.Entry(
            placeholder_text='A*',
            width_chars=8,
        )
        self.entry_node_weight.hide()
        self.entry_node_weight.connect('activate', self.update_node)
        box_node_propertys.append(self.entry_node_weight)

        # Подпись
        self.entry_node_desc = Gtk.Entry(
            placeholder_text='Надпись',
            tooltip_text='Личная надпись рядом с узлом',
            width_chars=10
        )
        self.entry_node_desc.hide()
        self.entry_node_desc.connect('activate', self.update_node)
        box_node_propertys.append(self.entry_node_desc)

        # Кнопошка цвета
        self.button_color = Gtk.ColorButton(
            height_request=32,
            tooltip_text='Цвет узла',
            hexpand=True
        )
        self.button_color.connect('color-set', self.update_node)
        self.set_color_to_button(self.button_color)
        box_node_propertys.append(self.button_color)

        self.right_panel.append(Gtk.Separator())

        ## Грани
        box_header_edges = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=5
        )
        self.right_panel.append(box_header_edges)
        box_header_edges.append(Gtk.Label(
            label='Связанные грани',
            hexpand=True
        ))

        self.button_add_edge = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='add',
            tooltip_text='Добавить грань',
            halign=Gtk.Align.END
        )
        self.button_add_edge.connect('clicked', self.add_edge_field)
        box_header_edges.append(self.button_add_edge)

        scrolled_window_r = Gtk.ScrolledWindow(
            vexpand=True,
            min_content_width=330,
            width_request=340
        )
        self.right_panel.append(scrolled_window_r)

        viewport_r = Gtk.Viewport()
        scrolled_window_r.set_child(viewport_r)

        self.box_edges = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=5,
            margin_bottom=5,
            margin_top=5
        )

        viewport_r.set_child(self.box_edges)

        # Текст предупреждения
        self.label_error = Gtk.Label(
            valign=Gtk.Align.END
        )
        self.right_panel.append(self.label_error)

        # Кнопошка приНЯть
        button_apply = Gtk.Button(
            label='Сохранить',
            margin_bottom=5
        )
        button_apply.connect('clicked', self.update_node)
        self.right_panel.append(button_apply)

    def add_edge_field(self, button=None, node2=None, weight=None, color=None):
        def destroy_box(button, field, eli):
            tname = eli[1].get_text()
            self.gui_edges.remove(eli)
            self.box_edges.remove(field)
            if tname != '':
                self.update_node()

        box_field = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=5
        )
        self.box_edges.append(box_field)
        entry_1 = Gtk.Entry(
            placeholder_text='Назначение',
            tooltip_text='Имя узла-назначения',
            hexpand=True,
            width_chars=12
        )
        entry_1.connect('activate', self.update_node)
        box_field.append(entry_1)
        box_field.append(Gtk.Label(label=':'))
        entry_2 = Gtk.Entry(
            placeholder_text='Расстояние',
            tooltip_text='Расстояние до назначения',
            width_chars=7
        )
        entry_2.connect('activate', self.update_node)
        box_field.append(entry_2)
        if self.switch_edges.get_active() is False:
            entry_2.hide()
        
        button_color_edge = Gtk.ColorButton(
            height_request=32,
            tooltip_text='Цвет узла'
        )
        button_color_edge.connect('color-set', self.update_node)
        box_field.append(button_color_edge)

        if node2:
            entry_1.set_text(node2)
        if weight:
            entry_2.set_text(str(weight))
        if color:
            color = self.rgb2hex(color)
            self.set_color_to_button(button_color_edge, color_hex=color)
        else:
            self.set_color_to_button(button_color_edge)

        button_rm = Gtk.Button(
            width_request=32,
            height_request=32,
            icon_name='edit-delete',
            tooltip_text='Удалить выбранную грань'
        )

        el = (box_field, entry_1, entry_2, button_color_edge)
        self.gui_edges.append(el)
        button_rm.connect('clicked', destroy_box, box_field, el)
        box_field.append(button_rm)

    def box_edges_clear(self):
        for field, _, _, _ in self.gui_edges:
            self.box_edges.remove(field)
        self.gui_edges.clear()

    def pop_dialog(self, button=None):
        def to_directed(button):
            self.G = nx.DiGraph()
            self.G.graph['graph'] = {'rankdir':'LR'}
            dialog.destroy()
            self.all_clear()
            self.label_di.set_label('DiGraph')

            self.redraw()
        
        def to_undirected(button):
            self.G = nx.Graph()
            self.G.graph['graph'] = {'rankdir':'LR'}
            dialog.destroy()
            self.all_clear()
            self.label_di.set_label('Graph')

            self.redraw()

        dialog = Gtk.Dialog(
            title='Выбор графа',
            modal=True,
            transient_for=self,
            resizable=False
        )
        dialog.set_default_size(300, 50)

        dialog_box = Gtk.Box(
            spacing=10,
            margin_start=5,
            margin_end=5,
            margin_bottom=5,
            margin_top=5,
            height_request=50,
            homogeneous=True
        )
        dialog.set_child(dialog_box)

        button_graph_1 = Gtk.Button(
            label='Направленный',
        )
        button_graph_1.connect('clicked', to_directed)
        dialog_box.append(button_graph_1)

        button_graph_2 = Gtk.Button(
            label='Ненаправленный'
        )
        button_graph_2.connect('clicked', to_undirected)
        dialog_box.append(button_graph_2)

        dialog.show()

    def set_color_to_button(self, button_color, color_hex='#9a9996'):
        color = Gdk.RGBA()
        Gdk.RGBA.parse(color, color_hex)
        button_color.set_rgba(color)


class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.window = MainWindow(application=app)
        self.window.present()

if __name__ == '__main__':
    app = App(application_id='com.github.me.myproject')
    app.run(sys.argv)