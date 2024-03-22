from odoo import models, fields


class MediaAttachment(models.Model):
    """
    Adding of `attachment_status` field to `ir.attachment` model to identify the
    current status of the file being attached.
    """
    _inherit = 'ir.attachment'

    attachment_status = fields.Selection([
        ('to_process', 'For Processing'),
        ('in_process', 'Process on going'),
        ('attached', 'Attached')
    ], default='attached')
