import warnings

# Silence Node.js deprecation noise that leaks through some transitive
# tooling during bulk downloads; doesn't affect the download logic itself.
warnings.filterwarnings("ignore", message=".*Node.*deprecat.*", category=DeprecationWarning)