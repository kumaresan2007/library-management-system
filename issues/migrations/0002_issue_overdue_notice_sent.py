from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="overdue_notice_sent",
            field=models.BooleanField(default=False),
        ),
    ]
