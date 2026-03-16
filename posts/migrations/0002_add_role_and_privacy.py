# ── HW8: Privacy Settings and Role-Based Access Control (RBAC) ───────────────
# This migration file is responsible for adding two new columns to the database.
# One column is for the role field on the User table and another is for the
# privacy field on the Post table. Instead of clearing and re-populating the
# entire database which would cause data loss, we chose Option 2 which means
# we simply add the new columns and let Django automatically fill in a default
# value for every existing row that does not have a value yet. This way all
# existing users and posts are kept exactly as they are and nothing is deleted.

# What this migration does:
#   Step 1: Adds the role column to the User table.
#           Every existing user row automatically gets role set to user
#           because that is the safe default. We do not want to accidentally
#           give every existing user admin access.
#   Step 2: Adds the privacy column to the Post table.
#           Every existing post row automatically gets privacy set to public
#           because those posts were created before this feature existed and
#           their authors always intended them to be visible to everyone.
# ── END HW8 ───────────────────────────────────────────────────────────────────

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Must run after the initial migration that created the tables
        ('posts', '0001_initial'),
    ]

    operations = [

        # ── Step 1: Add role to the User model ───────────────────────────────
        # The choices list tells Django which values are valid for this field.
        # Only admin, user, and guest are accepted. Any other value will be
        # rejected before it ever reaches the database.
        # The default value of user means every existing user row that did not
        # have a role before will now automatically be assigned the role of user.
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('user', 'User'), ('guest', 'Guest')],
                default='user',
                max_length=10,
            ),
        ),

        # ── Step 2: Add privacy to the Post model ────────────────────────────
        # The choices list tells Django which values are valid for this field.
        # Only public and private are accepted.
        # The default value of public means every existing post row that did not
        # have a privacy setting before will now automatically be set to public.
        # This is intentional so that existing posts remain visible to everyone
        # and do not suddenly disappear from the feed after the migration runs.
        migrations.AddField(
            model_name='post',
            name='privacy',
            field=models.CharField(
                choices=[('public', 'Public'), ('private', 'Private')],
                default='public',
                max_length=10,
            ),
        ),
    ]