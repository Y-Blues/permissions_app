import shutil
import unittest

from permissions_fixtures import create_manager

from ycappuccino.permissions.models.organization import Organization
from ycappuccino.permissions.organization_tree import OrganizationTree


async def _create_org(manager, id, father=None):
    organization = Organization()
    organization.id(id)
    organization.father(father)
    await manager.up_sert_model(organization)


class TestOrganizationTree(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.manager, directory = create_manager()
        self.addCleanup(shutil.rmtree, directory, True)

    async def test_a_leaf_organization_filters_on_itself_only(self):
        await _create_org(self.manager, "acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        condition = await tree.get_filter("book", {"tid": "acme"})

        self.assertEqual(condition, {"_tid": {"$in": ["acme"]}})

    async def test_children_and_grandchildren_are_included(self):
        await _create_org(self.manager, "acme")
        await _create_org(self.manager, "acme-eu", father="acme")
        await _create_org(self.manager, "acme-eu-fr", father="acme-eu")
        tree = OrganizationTree(self.manager)
        await tree.start()

        condition = await tree.get_filter("book", {"tid": "acme"})

        self.assertEqual(set(condition["_tid"]["$in"]), {"acme", "acme-eu", "acme-eu-fr"})

    async def test_a_sibling_subtree_is_not_included(self):
        await _create_org(self.manager, "acme")
        await _create_org(self.manager, "acme-eu", father="acme")
        await _create_org(self.manager, "acme-us", father="acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        condition = await tree.get_filter("book", {"tid": "acme-eu"})

        self.assertEqual(condition, {"_tid": {"$in": ["acme-eu"]}})

    async def test_execute_adds_a_new_organization_incrementally(self):
        await _create_org(self.manager, "acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        new_org = Organization()
        new_org.id("acme-us")
        new_org.father("acme")
        await tree.execute("upsert", "organization", new_org)

        condition = await tree.get_filter("book", {"tid": "acme"})
        self.assertIn("acme-us", condition["_tid"]["$in"])

    async def test_execute_removes_a_deleted_organization(self):
        await _create_org(self.manager, "acme")
        await _create_org(self.manager, "acme-eu", father="acme")
        tree = OrganizationTree(self.manager)
        await tree.start()

        deleted = Organization()
        deleted.id("acme-eu")
        await tree.execute("delete", "organization", deleted)

        condition = await tree.get_filter("book", {"tid": "acme"})
        self.assertNotIn("acme-eu", condition["_tid"]["$in"])

    async def test_it_watches_the_organization_upserts_and_deletes(self):
        self.assertEqual(OrganizationTree.item_id, "organization")
        self.assertEqual(OrganizationTree.actions, ("upsert", "delete"))
        self.assertTrue(OrganizationTree.post)


if __name__ == "__main__":
    unittest.main()
