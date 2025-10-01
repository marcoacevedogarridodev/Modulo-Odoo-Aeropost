{
    'name': 'TrackingAeropost',
    'version': '14.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Tracking Aeropost MIA y Status',
    'author': 'Mag',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',  
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': True,
}