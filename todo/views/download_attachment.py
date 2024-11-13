from django.http import HttpResponseForbidden, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from ..models import Attachment
from ..utils import user_can_download_attachment


@login_required
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)

    # Verifica se l'utente può accedere all'allegato
    if not user_can_download_attachment(attachment, request.user):
        return HttpResponse(status=403)

    # Controlla se il file esiste, altrimenti lancia un errore 404
    if not attachment.file:
        raise Http404("File not found.")

    # Crea una HttpResponse con il file come contenuto
    with open(attachment.file.path, 'rb') as file:
        response = HttpResponse(file.read(), content_type="application/octet-stream")
        response['Content-Disposition'] = f'attachment; filename="{attachment.filename()}"'

    return response
