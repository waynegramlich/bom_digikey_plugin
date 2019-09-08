def url_load(url, output_file_name, tracing=None):
    # Verify argument types:
    assert isinstance(url, str)
    assert isinstance(output_file_name, str)

    # Perform any requested *tracing*:
    next_tracing = None if tracing is None else tracing + " "
    if tracing is not None:
        print(f"{tracing}=>url_load('{url}', '{output_file_name}')")

    # Wrap up any requested *tracing*:
    if tracing is not None:
        print(f"{tracing}<=url_load('{url}', '{output_file_name}')")

