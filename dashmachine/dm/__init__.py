import os
import logging
import toml
from markupsafe import Markup
from dashmachine.dm.file_watcher import FileWatcher
from dashmachine.paths import (
    root_folder,
    dashboards_folder,
    settings_toml,
    data_sources_toml,
    shared_cards_toml,
)
from dashmachine.dm.settings import Settings
from dashmachine.dm.dashboard import Dashboard
from dashmachine.dm.data_source_handler import DataSourceHandler
from dashmachine.dm.utils import DEFAULT_QUERY_PROVIDERS


class DashMachine:
    def __init__(self, app):
        logging.info("DashMachine starting..")
        self.app = app
        self.query_providers = DEFAULT_QUERY_PROVIDERS
        self.settings = None
        self.data_source_handler = None
        self.dashboards = None
        self.main_dashboard = None
        self.shared_cards = []
        self.build()

        logging.info("File watchers starting..")
        self.settings_file_watcher = FileWatcher(settings_toml, self.build)
        self.dashboards_folder_watcher = FileWatcher(
            dashboards_folder, self.build, event="added"
        )
        self.data_sources_file_watcher = FileWatcher(data_sources_toml, self.build)
        self.shared_cards_file_watcher = FileWatcher(shared_cards_toml, self.build)
        self.dashboard_file_watchers = []
        for dboard_name, dboard in self.dashboards.items():
            self.dashboard_file_watchers.append(
                FileWatcher(dboard.toml_path, dboard.load_cards)
            )

    def build(self):
        # load settings
        self.settings = Settings()
        if hasattr(self.settings, "query_providers"):
            self.query_providers = self.settings.query_providers
        else:
            self.query_providers = DEFAULT_QUERY_PROVIDERS

        # load data_source handler
        self.data_source_handler = DataSourceHandler()

        # load shared cards
        self.shared_cards = self.load_shared_cards()

        # load dashboards
        self.dashboards = {}
        for file in os.listdir(dashboards_folder):
            self.dashboards[file.replace(".toml", "")] = Dashboard(file=file, dm=self)

        # pass any errors to the dashboards
        if self.settings.error:
            for dboard_name, dboard in self.dashboards.items():
                dboard.error = self.settings.error
            self.settings = Settings(read_toml=False)
        if self.data_source_handler.error:
            for dboard_name, dboard in self.dashboards.items():
                dboard.error = self.data_source_handler.error

        logging.info("DashMachine built")

    def get_dashboard_by_name(self, name):
        return (
            self.dashboards[name] if self.dashboards.get(name) else self.main_dashboard
        )

    @staticmethod
    def load_shared_cards():
        try:
            shared_cards = toml.load(shared_cards_toml)
        except Exception as e:
            logging.error("Could not load shard cards.", exc_info=True)
            return {}
        logging.info("Shared cards loaded")
        return shared_cards

    @staticmethod
    def get_logs():
        logs_path = os.path.join(root_folder, "dashmachine.log")
        if os.path.isfile(logs_path):
            with open(logs_path, "r") as logs_file:
                return Markup("<br>".join(logs_file.readlines()))
        else:
            return "Logs we deleted?"
