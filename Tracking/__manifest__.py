{
    'name': 'API Tracking',
    'version': '1.0',
    'summary': 'Sistema de busqueda de tracking en archivos Excel',
    'category': 'Tools',
    'author': 'MAG',
    'depends': ['base', 'web'],
    'data': [
        'views/tracking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Tracking/static/src/js/tracking.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}