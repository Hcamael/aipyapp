#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webbrowser

class HtmlExecutor():
    name = 'html'
    
    def __init__(self, runtime=None):
        self.runtime = runtime

    def __call__(self, block):
        abs_path = block.abs_path
        if abs_path:
            # Open the HTML file in a web browser
            import webbrowser
            webbrowser.open(f'file://{abs_path}')
        
        result = {'stdout': 'OK'}
        return result