import textwrap


def test():
    print(textwrap.dedent("""
    Title: {data.get('title_text')}
    Full Script ('script_text'): {data.get('script_text')}
    Gender: {data.get('gender')}
    Description: {data.get('description_text')}
    Hashtags: {data.get('hashtags')}
    """))


test()