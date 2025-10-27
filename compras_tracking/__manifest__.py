{
    'name': 'AutoPro Compras',
    'version': '14.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Tracking Aeropost MIA y Status',
    'description': '''
        Modulo de compras:
        - Nuevos campos en formulario de compra
        - Columnas adicionales en listas
        - Botones personalizados
    ''',
    'author': 'Mag',
    'depends': ['mblz_autopro', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',  
        'views/purchase_order_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}