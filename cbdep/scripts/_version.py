try:
    from _buildversion import __version__, __build__
except ImportError:
    __version__ = "0.0.0"
    __build__ = "9999"
