from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0018_profile_credentials_security'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recruitmentapplication',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('shortlisted', 'Shortlisted'), ('interview_scheduled', 'Interview Scheduled'), ('rejected', 'Rejected'), ('accepted', 'Accepted')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='volunteerhour',
            name='status',
            field=models.CharField(choices=[('assigned', 'Assigned'), ('accepted', 'Accepted'), ('completed', 'Completed'), ('verified', 'Verified')], default='assigned', max_length=20),
        ),
        migrations.AddField(
            model_name='eventstaffassignment',
            name='revoked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='eventstaffassignment',
            name='revoked_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='revoked_staff_assignments', to='core.user'),
        ),
    ]
