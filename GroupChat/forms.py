from django import forms
# from .models import ChatModel


class UploadChatFileForm(forms.Form):
    file = forms.FileField()
    # class Meta:
    #     model = ChatModel
    #     fields = ('title', 'txt')

    # name = forms.CharField(max_length=200)
    # file = forms.FileField()

