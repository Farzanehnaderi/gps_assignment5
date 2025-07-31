import sys
import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QSplitter, QGroupBox, QFormLayout, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QSpinBox, QProgressBar, QTextEdit, QTabWidget
)
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from Observation_gps import (
    extract_header_info,
    parse_observations,
    observations_to_dataframe,
    save_to_csv,
    datetime_to_gps_seconds
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RINEX C1C Analyzer")
        self.resize(1200, 700)

        self.obs_records = []
        self.df = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(QtCore.Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        splitter.addWidget(left_panel)

        grp_file = QGroupBox("RINEX File")
        f_layout = QHBoxLayout(grp_file)
        self.le_file = QLineEdit()
        self.bt_browse = QPushButton("Browse...")
        f_layout.addWidget(self.le_file)
        f_layout.addWidget(self.bt_browse)
        left_layout.addWidget(grp_file)

        grp_header = QGroupBox("Header Info")
        h_form = QFormLayout(grp_header)
        self.lb_version = QLabel("-")
        self.lb_obs_types = QLabel("-")
        self.lb_c1c_idx = QLabel("-")
        h_form.addRow("Version:", self.lb_version)
        h_form.addRow("Obs Types:", self.lb_obs_types)
        h_form.addRow("C1C Index:", self.lb_c1c_idx)
        left_layout.addWidget(grp_header)

        self.bt_parse = QPushButton("Parse Observations")
        left_layout.addWidget(self.bt_parse)

        grp_sats = QGroupBox("Satellite Selection")
        s_layout = QVBoxLayout(grp_sats)
        self.list_sats = QListWidget()
        self.list_sats.setSelectionMode(QListWidget.MultiSelection)
        self.spin_count = QSpinBox()
        self.spin_count.setRange(0, 50)
        self.spin_count.setPrefix("First ")
        self.spin_count.setSuffix(" sats")
        s_layout.addWidget(self.list_sats)
        s_layout.addWidget(self.spin_count)
        left_layout.addWidget(grp_sats)

        grp_actions = QGroupBox("Actions")
        a_layout = QHBoxLayout(grp_actions)
        self.bt_save = QPushButton("Save CSV")
        self.bt_plot = QPushButton("Plot")
        a_layout.addWidget(self.bt_save)
        a_layout.addWidget(self.bt_plot)
        left_layout.addWidget(grp_actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        left_layout.addWidget(self.progress)
        self.statusBar()

        right_tabs = QTabWidget()
        splitter.addWidget(right_tabs)

        tab_plot = QWidget()
        plot_layout = QVBoxLayout(tab_plot)
        self.canvas = FigureCanvas(plt.Figure())
        self.toolbar = NavigationToolbar(self.canvas, self)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        right_tabs.addTab(tab_plot, "Plot")

        tab_console = QWidget()
        console_layout = QVBoxLayout(tab_console)
        self.te_log = QTextEdit()
        self.te_log.setReadOnly(True)
        console_layout.addWidget(self.te_log)
        right_tabs.addTab(tab_console, "Console")

        QApplication.setStyle("Fusion")
        dark_palette = QtGui.QPalette()
        dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(35, 35, 35))
        dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(142, 45, 197).lighter())
        dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        QApplication.setPalette(dark_palette)

    def _connect_signals(self):
        self.bt_browse.clicked.connect(self.on_browse)
        self.bt_parse.clicked.connect(self.on_parse)
        self.bt_save.clicked.connect(self.on_save_csv)
        self.bt_plot.clicked.connect(self.on_plot)

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.te_log.append(f"{timestamp}  {message}")

    def on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select RINEX File", "", "RINEX Files (*.*O *.*o);;All Files (*)"
        )
        if path:
            self.le_file.setText(path)

    def on_parse(self):
        filepath = self.le_file.text().strip()
        if not filepath:
            QMessageBox.warning(self, "Warning", "Please select a RINEX file first.")
            return

        try:
            self.statusBar().showMessage("Reading header...")
            info = extract_header_info(filepath)
            self.lb_version.setText(info["version"])
            self.lb_obs_types.setText(", ".join(info["obs_types"]))
            self.lb_c1c_idx.setText(str(info["c1c_index"]))

            self.log("Header parsed successfully.")
            self.statusBar().showMessage("Parsing observations...")

            self.obs_records = parse_observations(filepath, info["c1c_index"])
            self.df = observations_to_dataframe(self.obs_records)

            sats = sorted(self.df["Satellite"].unique())
            self.list_sats.clear()
            for prn in sats:
                self.list_sats.addItem(QListWidgetItem(prn))
            self.spin_count.setMaximum(len(sats))

            self.log(f"Parsed {len(self.obs_records)} epochs with {len(sats)} satellites.")
            self.statusBar().showMessage("Ready")
            self.progress.setValue(100)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.log(f"Error: {e}")
            self.statusBar().showMessage("Error")
            self.progress.setValue(0)

    def on_save_csv(self):
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "Warning", "No data to save. Please parse first.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save CSV Report", "c1c_report.csv", "CSV Files (*.csv)"
        )
        if not filename:
            return

        try:
            out_path = save_to_csv(self.df, filename)
            self.log(f"CSV saved to: {out_path}")
            QMessageBox.information(self, "Success", f"CSV saved to:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.log(f"Error: {e}")

    def on_plot(self):
        if self.df is None or self.df.empty:
            QMessageBox.warning(self, "Warning", "No data to plot. Please parse first.")
            return

        selected = [item.text() for item in self.list_sats.selectedItems()]
        count = self.spin_count.value()
        if count > 0:
            selected = sorted(self.df["Satellite"].unique())[:count]
        if not selected:
            selected = sorted(self.df["Satellite"].unique())[:4]

        fig = self.canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        df2 = self.df.copy()
        df2["GPS_Seconds"] = df2["Time"].apply(datetime_to_gps_seconds)

        colors = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854']
        markers = ['o', 'v', 's', '^', 'D']

        for idx, sat in enumerate(selected):
            sat_df = df2[df2["Satellite"] == sat]
            if sat_df.empty:
                continue

            ax.plot(
                sat_df["Time"],
                sat_df["C1C_m"],
                label=sat,
                color=colors[idx % len(colors)],
                marker=markers[idx % len(markers)],
                markersize=4,
                linewidth=1.2,
                alpha=0.9
            )

            if idx == 0:
                max_idx = sat_df["C1C_m"].idxmax()
                t0 = sat_df.loc[max_idx, "Time"]
                v0 = sat_df.loc[max_idx, "C1C_m"]
                ax.annotate(
                    f"Max {sat}",
                    xy=(t0, v0),
                    xytext=(t0, v0 + 500),
                    arrowprops=dict(arrowstyle='->', color='gray'),
                    fontsize=9,
                    color='black'
                )

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("C1C Pseudorange [m]")
        ax.set_title("C1C Pseudorange vs Time", fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.7)
        ax.legend(title="Satellites", loc='upper center', ncol=len(selected)).get_frame().set_alpha(0.8)

        fig.tight_layout()
        self.canvas.draw()
        self.log("Plot updated.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
