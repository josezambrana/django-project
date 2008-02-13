from django import newforms as forms
from django.newforms import ValidationError
import re

from models import *
from django.utils.translation import ugettext as _ 

class CreateProjectForm(forms.Form):
    #shortname = DojoCharField(max_length = 20, widget=forms.TextInput(attrs={'dojoType':'dijit.form.TextBox'}))
    shortname = DojoCharField(max_length = 20)
    name = DojoCharField(max_length = 200, widget=forms.TextInput(attrs={'dojoType':'dijit.form.TextBox'}))
    
    def __init__(self, user = None, *args, **kwargs):
        super(CreateProjectForm, self).__init__(*args, **kwargs)
        self.user = user
    
    def save(self):
        project = Project(name = self.cleaned_data['name'], shortname=self.cleaned_data['shortname'])
        project.owner = self.user
        project.save()
        subscribe = SubscribedUser(user = self.user, project = project, group = 'OWN')
        subscribe.save()
        return project
    
    def clean_shortname(self):
        alnum_re = re.compile(r'^\w+$')
        if not alnum_re.search(self.cleaned_data['shortname']):
            raise ValidationError("This value must contain only letters, numbers and underscores.")
        self.is_valid_shortname()
        return self.cleaned_data['shortname']
    
    def is_valid_shortname(self):
        try:
            Project.objects.get(shortname = self.cleaned_data['shortname'])
        except Project.DoesNotExist:
            return
        raise ValidationError('This project name is already taken. Please try another.')
    
class InviteUserForm(forms.Form):
    username = DojoCharField(max_length = 30)
    group = DojoChoiceField(choices = options)
    
    def __init__(self, project = None, *args, **kwargs):
        super(InviteUserForm, self).__init__(*args, **kwargs)
        self.project = project
        
    def clean_username(self):
        try:
            User.objects.get(username = self.cleaned_data['username'])
        except User.DoesNotExist:
            raise ValidationError('There is no user with that name')
        self.already_invited()
        self.already_subscribed()
        return self.cleaned_data['username']
    
    def already_invited(self):
        try:
            user = User.objects.get(username = self.cleaned_data['username'])
            invite = user.inviteduser_set.get(user = user, project = self.project)
        except InvitedUser.DoesNotExist:
            return    
        raise ValidationError('This user is already invited. The invite is pending.')
        
    def already_subscribed(self):
        try:
            user = User.objects.get(username = self.cleaned_data['username'])
            subs = user.subscribeduser_set.get(user = user, project = self.project)
        except SubscribedUser.DoesNotExist:
            return    
        raise ValidationError('This user is already subscribed to the project.')
        
    def save(self):
        user = User.objects.get(username = self.cleaned_data['username'])
        invite = InvitedUser(user = user, project = self.project)
        invite.group = self.cleaned_data['group']
        invite.save()
        return invite
        
class CreateTaskForm(forms.Form):
    name = DojoCharField(max_length = 200)
    start_date = DojoDateField()#forms.DateField(widget = forms.TextInput(attrs = {'dojoType':'dijit.form.DateTextBox'}))
    end_date = DojoDateField(required = False)#forms.DateField(required = False)
    user_responsible = DojoChoiceField()#forms.ChoiceField()
    def __init__(self, project = None, *args, **kwargs):
        super(CreateTaskForm, self).__init__(*args, **kwargs)
        self.project = project
        users = [subs.user for subs in project.subscribeduser_set.all()]
        self.fields['user_responsible'].choices = [('None','None')] + [(user.username, user.username) for user in users]
        
    def clean(self):
        if self.cleaned_data['end_date'] and self.cleaned_data['start_date'] > self.cleaned_data['end_date']:
            raise ValidationError('Start date can not be greater than end date')
        return super(CreateTaskForm, self).clean()
        
    def save_without_db(self):
        task = Task(name = self.cleaned_data['name'], expected_start_date = self.cleaned_data['start_date'], )
        if self.cleaned_data['end_date']:
            task.expected_end_date = self.cleaned_data['end_date']
        if not self.cleaned_data['user_responsible'] == 'None':
            user = User.objects.get(username = self.cleaned_data['user_responsible'])
            task.user_responsible = user
        task.project = self.project
        return task        
        
    def save(self):
        task = self.save_without_db()
        task.save()
        return task


class CreateSubTaskForm(CreateTaskForm):
    def __init__(self, project = None, parent_task = None, *args, **kwargs):
        super(CreateSubTaskForm, self).__init__(project, *args, **kwargs)
        self.parent_task = parent_task
    def save(self):
        task = self.save_without_db()
        task.parent_task = self.parent_task
        task.save()
        return task
        
        
class CreateTaskItemForm(forms.Form):
    item_name = DojoCharField(max_length = 200)
    user = DojoChoiceField()
    time = DojoDecimalField()
    units = DojoChoiceField(choices = unit_choices)
    def __init__(self, task = None, *args, **kwargs):
        super(CreateTaskItemForm, self).__init__(*args, **kwargs)
        self.task = task
        users = [subs.user for subs in task.project.subscribeduser_set.all()]
        self.fields['user'].choices = [('None','None')] + [(user.username, user.username) for user in users]
        
    def clean(self):
        if self.cleaned_data['time'] <= 0:
            raise ValidationError('Time must be greater than 0')
        return super(CreateTaskItemForm, self).clean()
        
    def save(self):
        item = TaskItem(name = self.cleaned_data['item_name'], )
        item.task = self.task
        if not self.cleaned_data['user'] == 'None':
            user = User.objects.get(username = self.cleaned_data['user'])
            item.user = user
        item.expected_time = self.cleaned_data['time']
        item.unit = self.cleaned_data['units']
        item.save()
        return item
        


class AddNoticeForm(forms.Form):
    text = DojoCharField(widget = forms.Textarea)
    
    def __init__(self, project = None, user = None, *args, **kwargs):
        super(AddNoticeForm, self).__init__(*args, **kwargs)
        self.project = project
        self.user = user
        
    def save(self):
        notice = Notice(text = self.cleaned_data['text'], user = self.user, project = self.project)
        notice.save()
        return notice
    
class AddTodoListForm(forms.Form):
    name = DojoCharField()
    
    def __init__(self, project = None, user = None, *args, **kwargs):
        super(AddTodoListForm, self).__init__(*args, **kwargs)
        self.project = project
        self.user = user
        
    def save(self):
        list = TodoList(name = self.cleaned_data['name'], user = self.user, project = self.project)
        list.save()
        return list

class CreateWikiPageForm(forms.Form):
    title = DojoCharField()
    text = DojoTextArea()
    #text = DojoCharField(widget = forms.Textarea)
    
    def __init__(self, project = None, user = None, *args, **kwargs):
        super(CreateWikiPageForm, self).__init__(*args, **kwargs)
        self.project = project
        self.user = user
        
    def save(self):
        page = WikiPage(title = self.cleaned_data['title'],)
        page.project = self.project
        page.save()
        
        page_rev = WikiPageRevision(wiki_text = self.cleaned_data['text'])
        page_rev.wiki_page = page
        page_rev.user = self.user
        page_rev.save()
        
        page.current_revision = page_rev
        page.save()
        return page
        
class EditWikiPageForm(forms.Form):
    text = DojoTextArea()#DojoCharField(widget = forms.Textarea)
    
    def __init__(self, user = None, page = None, *args, **kwargs):
        super(EditWikiPageForm, self).__init__(*args, **kwargs)
        self.page = page
        self.user = user
        self.fields['text'].initial = page.current_revision.wiki_text
    
    def save(self):
        page_rev = WikiPageRevision(wiki_text = self.cleaned_data['text'])
        page_rev.wiki_page = self.page
        page_rev.user = self.user
        page_rev.save()
        
        self.page.current_revision = page_rev
        self.page.save()


"""
class EditTaskForm(forms.ModelForm):
    expected_end_date = DojoDateField(required = False)
    actual_start_date = DojoDateField(required = False)
    actual_end_date = DojoDateField(required = False)
    user_responsible = DojoChoiceField()
    
    def __init__(self, *args, **kwargs):
        super(EditTaskForm, self).__init__(*args, **kwargs)
        users = [subs.user for subs in self.instance.project.subscribeduser_set.all()]
        self.fields['user_responsible'].choices = [('None','None')] + [(user.username, user.username) for user in users]

    class Meta:
        model = Task
        exclude = ('number', 'project', 'parent_task', 'version_number', 'is_current', 'effective_end_date')
"""

class EditTaskForm(CreateTaskForm):
    actual_start_date = DojoDateField(required = False)
    actual_end_date = DojoDateField(required = False)
    is_complete = forms.BooleanField()
    
    def __init__(self, project, task, *args, **kwargs):
        super(EditTaskForm, self).__init__(project, *args, **kwargs)
        self.task = task
        self.fields['name'].initial = task.name
        self.fields['start_date'].initial = task.expected_start_date
        self.fields['end_date'].initial = task.expected_end_date
        self.fields['actual_start_date'].initial = task.actual_start_date
        self.fields['actual_end_date'].initial = task.actual_end_date
        self.fields['is_complete'].initial = task.is_complete
        if task.user_responsible:
            self.fields['user_responsible'].initial = task.user_responsible
    
    def save(self):
        task = self.task
        task.name = self.cleaned_data['name']
        task.user_responsible = self.cleaned_data['user_responsible']
        task.expected_start_date = self.cleaned_data['start_date']
        if self.cleaned_data['end_date']:
            task.expected_end_date = self.cleaned_data['end_date']
        if self.cleaned_data['actual_start_date']:
            task.actual_start_date = self.cleaned_data['actual_start_date']
        if self.cleaned_data['actual_end_date']:
            task.actual_end_date = self.cleaned_data['actual_end_date']
        task.is_complete_prop = self.cleaned_data['is_complete']
        task.save()
        return task
            
class EditTaskItemForm(forms.ModelForm):
    user = DojoChoiceField()
    
    def __init__(self, *args, **kwargs):
        super(EditTaskItemForm, self).__init__(*args, **kwargs)
        users = [subs.user for subs in self.instance.task.project.subscribeduser_set.all()]
        self.fields['user'].choices = [('None','None')] + [(user.username, user.username) for user in users]    
    
    class Meta:
        model = TaskItem
        exclude = ('task', 'version_number', 'is_current', 'effective_end_date')
        
class AddTaskNoteForm(forms.Form):
    text = DojoCharField(widget = forms.Textarea)
    
    def __init__(self, task, user, *args, **kwargs):
        super(AddTaskNoteForm, self).__init__(*args, **kwargs)
        self.task = task
        self.user = user
        
    def save(self):
        note = self.task.add_note(text = self.cleaned_data['text'], user = self.user)
        return note
    
    
class UserCreationForm(forms.Form):
    """A form that creates a user, with no privileges, from the given username and password."""
    username = DojoCharField(max_length = 30, required = True)
    password1 = DojoCharField(max_length = 30, required = True, widget = forms.PasswordInput)
    password2 = DojoCharField(max_length = 30, required = True, widget = forms.PasswordInput)
    project_name = DojoCharField(max_length = 20, required = False)

    def clean_username (self):
        alnum_re = re.compile(r'^\w+$')
        if not alnum_re.search(self.cleaned_data['username']):
            raise ValidationError("This value must contain only letters, numbers and underscores.")
        self.isValidUsername()
        return self.cleaned_data['username']

    def clean (self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise ValidationError(_("The two password fields didn't match."))
        return super(forms.Form, self).clean()
        
    def isValidUsername(self):
        try:
            User.objects.get(username=self.cleaned_data['username'])
        except User.DoesNotExist:
            return
        raise ValidationError(_('A user with that username already exists.'))
    
    def clean_project_name(self):
        alnum_re = re.compile(r'^\w+$')
        if not alnum_re.search(self.cleaned_data['project_name']):
            raise ValidationError("This value must contain only letters, numbers and underscores.")
        self.is_valid_shortname()
        return self.cleaned_data['project_name']
    
    def is_valid_shortname(self):
        try:
            Project.objects.get(shortname = self.cleaned_data['project_name'])
        except Project.DoesNotExist:
            return
        raise ValidationError('This project name is already taken. Please try another.')
    
    def save(self):
        return User.objects.create_user(self.cleaned_data['username'], '', self.cleaned_data['password1'])

     
    
