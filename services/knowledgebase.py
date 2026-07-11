"""
知识库相关服务
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.minio import MinioClient
from models.knowledgebase import KnowledgeBase, KnowledgeCategory
from config.settings import settings
from utils.pagination import PageData, paginate


class KnowledgeCategoryService:
    """知识库分类服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client = MinioClient()

    async def _get_path(self, category_id) -> str:
        """获取分类的完整路径"""
        if category_id == 0 or category_id is None:
            return ""
        cat = await self.get_by_id(category_id)
        if not cat:
            return ""
        if cat.parent_id == 0 or cat.parent_id is None:
            return cat.name
        parent_path = await self._get_path(cat.parent_id)
        return f"{parent_path}/{cat.name}" if parent_path else cat.name

    async def create(self, name: str, creator_id: str, description: str = None, icon: str = None, parent_id: int = 0, sort_order: int = 0) -> KnowledgeCategory:
        """创建分类"""
        category = KnowledgeCategory(
            name=name,
            description=description,
            icon=icon,
            parent_id=parent_id,
            sort_order=sort_order,
            creator_id=creator_id
        )
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)

        # 在 MinIO 创建对应目录
        await self.minio_client.init()
        path = await self._get_path(category.id)
        if path:
            await self.minio_client.ensure_directory(settings.MINIO_BUCKET, f"knowledge/{path}")

        return category

    async def get_by_id(self, category_id) -> Optional[KnowledgeCategory]:
        """根据 ID 获取分类"""
        return await self.db.get(KnowledgeCategory, category_id)

    async def get_list(self, page: int = 1, size: int = 20, keyword: str = None) -> dict:
        """获取分类列表（过滤已删除，支持模糊搜索）"""
        from models.user import User

        count_stmt = select(func.count()).select_from(KnowledgeCategory).where(KnowledgeCategory.is_deleted == False)
        stmt = select(KnowledgeCategory).where(KnowledgeCategory.is_deleted == False)

        # 模糊搜索
        if keyword:
            count_stmt = count_stmt.where(KnowledgeCategory.name.ilike(f"%{keyword}%"))
            stmt = stmt.where(KnowledgeCategory.name.ilike(f"%{keyword}%"))

        total = (await self.db.execute(count_stmt)).scalar()
        stmt = stmt.order_by(KnowledgeCategory.sort_order, KnowledgeCategory.id).offset((page - 1) * size).limit(size)
        result = await self.db.execute(stmt)
        categories = result.scalars().all()

        # 查询创建人信息
        items = []
        for cat in categories:
            user = await self.db.get(User, cat.creator_id) if cat.creator_id else None
            items.append({
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "parent_id": cat.parent_id,
                "sort_order": cat.sort_order,
                "creator_id": cat.creator_id,
                "creator_name": user.username if user else None,
                "created_at": cat.created_at
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size
        }

    async def update(self, category_id, user_id: str, **kwargs) -> dict:
        """更新分类"""
        category = await self.get_by_id(category_id)
        if not category:
            return {"success": False, "message": "分类不存在"}

        # 权限检查：只有创建人可以修改
        if category.creator_id and category.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以修改"}

        for key, value in kwargs.items():
            if value is not None and hasattr(category, key):
                setattr(category, key, value)

        await self.db.commit()
        await self.db.refresh(category)
        return {"success": True, "data": category}

    async def delete(self, category_id, user_id: str) -> dict:
        """删除分类（逻辑删除）"""
        category = await self.get_by_id(category_id)
        if not category:
            return {"success": False, "message": "分类不存在"}

        # 权限检查：只有创建人可以删除
        if category.creator_id and category.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以删除"}

        category.is_deleted = True
        await self.db.commit()
        return {"success": True, "message": "删除成功"}


class KnowledgeBaseService:
    """知识库服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.minio_client = MinioClient()

    async def _is_descendant(self, ancestor_id: str, target_id: str) -> bool:
        """检查 target 是否是 ancestor 的后代"""
        current_id = target_id
        while current_id and current_id != "0":
            if current_id == ancestor_id:
                return True
            item = await self.get_by_id(current_id)
            if not item:
                break
            current_id = item.parent_id
        return False

    async def _get_unique_name(self, name: str, parent_id: str, is_folder: bool = False) -> str:
        """获取唯一名称（自动重命名避免冲突）"""
        # 查询同级同类型的同名项
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.parent_id == parent_id,
            KnowledgeBase.is_folder == is_folder,
            KnowledgeBase.is_deleted == False
        )
        result = await self.db.execute(stmt)
        existing_items = {item.name for item in result.scalars().all()}

        if name not in existing_items:
            return name

        # 分离文件名和扩展名
        if is_folder or "." not in name:
            base_name = name
            ext = ""
        else:
            base_name, ext = os.path.splitext(name)
            ext = ext  # 保留扩展名

        # 递增编号找到第一个不冲突的
        n = 1
        while True:
            new_name = f"{base_name}({n}){ext}"
            if new_name not in existing_items:
                return new_name
            n += 1

    async def create_folder(self, name: str, creator_id: str, parent_id: str = "0", category_id: str = None) -> KnowledgeBase:
        """创建文件夹（只在数据库中维护，不在 MinIO 创建目录）"""
        # parent_id 为空时默认为 "0"
        if not parent_id:
            parent_id = "0"

        # 自动重命名避免冲突
        name = await self._get_unique_name(name, parent_id, is_folder=True)

        # 构建路径
        if parent_id == "0":
            path = f"{name}/"
            level = 0
        else:
            parent = await self.get_by_id(parent_id)
            if not parent:
                raise ValueError("父文件夹不存在")
            path = f"{parent.path}{name}/"
            level = parent.level + 1

        folder = KnowledgeBase(
            name=name,
            file_ext="",
            minio_key="",
            status="folder",
            creator_id=creator_id,
            category_id=category_id,
            is_folder=True,
            parent_id=parent_id,
            path=path,
            level=level
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)
        return folder

    async def upload_file(self, file_name: str, file_content: bytes, file_ext: str, creator_id: str, parent_id: str = "0", category_id: str = None, content_type: str = None) -> KnowledgeBase:
        """上传文件"""
        # 初始化 MinIO
        await self.minio_client.init()

        # parent_id 为空时默认为 "0"
        if not parent_id:
            parent_id = "0"

        # 自动重命名避免冲突（保留扩展名）
        file_name = await self._get_unique_name(file_name, parent_id, is_folder=False)

        # 生成唯一文件名
        import uuid
        file_uuid = str(uuid.uuid4())
        unique_file_name = f"{file_uuid}_{file_name}"

        # 获取分类路径
        cat_path = ""
        if category_id:
            category_service = KnowledgeCategoryService(self.db)
            cat_path = await category_service._get_path(category_id)

        # 构建数据库路径（显示用，包含文件夹层级）
        if parent_id == "0":
            path = f"{cat_path}/{file_name}" if cat_path else file_name
            level = 0
        else:
            parent = await self.get_by_id(parent_id)
            if not parent:
                raise ValueError("父文件夹不存在")
            path = f"{parent.path}{file_name}"
            level = parent.level + 1

        # MinIO 存储路径：只按分类层级，不按文件夹层级
        minio_key = f"knowledge/{cat_path}/{unique_file_name}" if cat_path else f"knowledge/{unique_file_name}"

        await self.minio_client.upload_data(
            bucket_name=settings.MINIO_BUCKET,
            object_name=minio_key,
            data=file_content,
            content_type=content_type or "application/octet-stream"
        )

        # 保存到数据库
        kb = KnowledgeBase(
            name=file_name,
            file_ext=file_ext,
            file_size=len(file_content),
            minio_key=minio_key,
            status="uploaded",
            creator_id=creator_id,
            category_id=category_id,
            is_folder=False,
            parent_id=parent_id,
            path=path,
            level=level
        )
        self.db.add(kb)
        await self.db.commit()
        await self.db.refresh(kb)
        return kb

    async def get_by_id(self, kb_id) -> Optional[KnowledgeBase]:
        """根据 ID 获取"""
        return await self.db.get(KnowledgeBase, kb_id)

    async def search(self, keyword: str, category_id: str = None, parent_id: str = None, page: int = 1, size: int = 20) -> PageData:
        """搜索文件/文件夹（Windows 风格，平铺返回）"""
        from models.user import User

        stmt = select(KnowledgeBase).where(KnowledgeBase.is_deleted == False)

        # 按分类筛选
        if category_id:
            stmt = stmt.where(KnowledgeBase.category_id == category_id)

        # 按父级路径筛选（递归子目录）
        if parent_id:
            parent = await self.get_by_id(parent_id)
            if parent:
                stmt = stmt.where(KnowledgeBase.path.startswith(parent.path))

        # 关键词搜索
        if keyword:
            stmt = stmt.where(KnowledgeBase.name.ilike(f"%{keyword}%"))

        # 排序：文件夹在前，按更新时间降序
        stmt = stmt.order_by(KnowledgeBase.is_folder.desc(), KnowledgeBase.updated_at.desc())

        # 分页查询
        page_data = await paginate(self.db, stmt, page, size)

        # 补充创建人信息
        items = []
        for kb in page_data.items:
            user = await self.db.get(User, kb.creator_id) if kb.creator_id else None
            items.append({
                "id": kb.id,
                "name": kb.name,
                "file_ext": kb.file_ext,
                "file_size": kb.file_size,
                "minio_key": kb.minio_key,
                "status": kb.status,
                "creator_id": kb.creator_id,
                "creator_name": user.username if user else None,
                "is_folder": kb.is_folder,
                "parent_id": kb.parent_id,
                "path": kb.path,
                "level": kb.level,
                "sort_order": kb.sort_order,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at
            })

        return PageData(
            items=items,
            total=page_data.total,
            page=page_data.page,
            size=page_data.size
        )

    async def get_list(self, page: int = 1, size: int = 20, parent_id: str = "0", category_id: str = None, keyword: str = None) -> PageData:
        """获取列表（分页，过滤已删除，支持模糊搜索）"""
        from models.user import User
        from utils.pagination import paginate

        stmt = select(KnowledgeBase).where(KnowledgeBase.is_deleted == False)

        # 按分类筛选
        if category_id:
            stmt = stmt.where(KnowledgeBase.category_id == category_id)

        # 按父级筛选
        stmt = stmt.where(KnowledgeBase.parent_id == parent_id)

        # 模糊搜索
        if keyword:
            stmt = stmt.where(KnowledgeBase.name.ilike(f"%{keyword}%"))

        # 排序
        stmt = stmt.order_by(KnowledgeBase.is_folder.desc(), KnowledgeBase.updated_at.desc())

        # 分页查询
        page_data = await paginate(self.db, stmt, page, size)

        # 补充创建人信息
        items = []
        for kb in page_data.items:
            user = await self.db.get(User, kb.creator_id) if kb.creator_id else None
            items.append({
                "id": kb.id,
                "name": kb.name,
                "file_ext": kb.file_ext,
                "file_size": kb.file_size,
                "minio_key": kb.minio_key,
                "parsed_minio_key": kb.parsed_minio_key,
                "status": kb.status,
                "creator_id": kb.creator_id,
                "creator_name": user.username if user else None,
                "is_folder": kb.is_folder,
                "parent_id": kb.parent_id,
                "path": kb.path,
                "level": kb.level,
                "sort_order": kb.sort_order,
                "title": kb.title,
                "created_at": kb.created_at,
                "updated_at": kb.updated_at
            })

        return PageData(
            items=items,
            total=page_data.total,
            page=page_data.page,
            size=page_data.size
        )

    async def get_navigation(self, kb_id: str) -> list:
        """获取面包屑导航路径"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return []

        # 从当前节点向上追溯到根节点
        navigation = []
        current_id = kb_id

        while current_id and current_id != "0":
            item = await self.get_by_id(current_id)
            if not item:
                break
            navigation.append({
                "id": item.id,
                "name": item.name,
                "path": item.path,
                "is_folder": item.is_folder
            })
            current_id = item.parent_id

        # 反转，从根到当前
        navigation.reverse()

        # 添加根节点
        navigation.insert(0, {
            "id": "0",
            "name": "全部文件",
            "path": "/",
            "is_folder": True
        })

        return navigation

    async def get_children(self, parent_id: int = 0) -> list:
        """获取子项（不分页，过滤已删除）"""
        stmt = select(KnowledgeBase).where(KnowledgeBase.parent_id == parent_id, KnowledgeBase.is_deleted == False).order_by(KnowledgeBase.is_folder.desc(), KnowledgeBase.sort_order, KnowledgeBase.id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_folder_tree(self, parent_id: str = "0", category_id: str = None) -> list:
        """获取文件夹树（用于选择目标路径，只返回文件夹）"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.is_deleted == False,
            KnowledgeBase.is_folder == True,
            KnowledgeBase.parent_id == parent_id
        )
        if category_id:
            stmt = stmt.where(KnowledgeBase.category_id == category_id)
        stmt = stmt.order_by(KnowledgeBase.sort_order, KnowledgeBase.name)

        result = await self.db.execute(stmt)
        folders = result.scalars().all()

        tree = []
        for folder in folders:
            node = {
                "id": folder.id,
                "name": folder.name,
                "path": folder.path,
            }
            # 递归获取子文件夹
            children = await self.get_folder_tree(folder.id, category_id)
            if children:
                node["children"] = children
            tree.append(node)

        return tree

    async def get_tree(self, parent_id: int = 0) -> list:
        """获取树形结构"""
        items = await self.get_children(parent_id)
        tree = []
        for item in items:
            node = {
                "id": item.id,
                "name": item.name,
                "is_folder": item.is_folder,
                "path": item.path,
                "level": item.level,
                "file_ext": item.file_ext,
                "status": item.status,
                "creator_id": item.creator_id,
                "created_at": str(item.created_at) if item.created_at else None
            }
            if item.is_folder:
                node["children"] = await self.get_tree(item.id)
            tree.append(node)
        return tree

    async def update(self, kb_id, user_id: str, **kwargs) -> dict:
        """更新"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        # 权限检查：只有创建人可以修改
        if kb.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以修改"}

        for key, value in kwargs.items():
            if value is not None and hasattr(kb, key):
                setattr(kb, key, value)

        await self.db.commit()
        await self.db.refresh(kb)
        return {"success": True, "data": kb}

    async def copy(self, kb_id, target_parent_id: str, user_id: str) -> dict:
        """复制文件/文件夹"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        # 权限检查
        if kb.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以复制"}

        # 处理空值
        if not target_parent_id:
            target_parent_id = "0"

        # 不能复制到自己里面
        if target_parent_id == kb_id:
            return {"success": False, "message": "不能复制到自身"}

        # 不能复制到自己的子文件夹（防止无限递归）
        if kb.is_folder and target_parent_id != "0":
            if await self._is_descendant(kb_id, target_parent_id):
                return {"success": False, "message": "不能复制到自身的子文件夹"}

        # 目标文件夹
        if target_parent_id == "0":
            target_path = ""
            target_level = 0
        else:
            target_folder = await self.get_by_id(target_parent_id)
            if not target_folder:
                return {"success": False, "message": "目标文件夹不存在"}
            target_path = target_folder.path
            target_level = target_folder.level + 1

        # 自动重命名
        new_name = await self._get_unique_name(kb.name, target_parent_id, kb.is_folder)

        if kb.is_folder:
            # 复制文件夹
            new_kb = KnowledgeBase(
                name=new_name,
                file_ext="",
                minio_key="",
                status="folder",
                creator_id=user_id,
                category_id=kb.category_id,
                is_folder=True,
                parent_id=target_parent_id,
                path=f"{target_path}{new_name}/",
                level=target_level
            )
            self.db.add(new_kb)
            await self.db.commit()
            await self.db.refresh(new_kb)

            # 递归复制子项
            children = await self.get_children(kb_id)
            for child in children:
                await self.copy(child.id, new_kb.id, user_id)

        else:
            # 复制文件
            new_minio_key = ""
            if kb.minio_key:
                await self.minio_client.init()
                # 生成新的 MinIO key
                import uuid
                new_file_uuid = str(uuid.uuid4())
                file_name = kb.name
                new_minio_key = f"knowledge/{kb.category_id}/{new_file_uuid}_{file_name}" if kb.category_id else f"knowledge/{new_file_uuid}_{file_name}"

                # 复制 MinIO 文件
                try:
                    file_data = await self.minio_client.get_object(settings.MINIO_BUCKET, kb.minio_key)
                    await self.minio_client.upload_data(
                        bucket_name=settings.MINIO_BUCKET,
                        object_name=new_minio_key,
                        data=file_data,
                        content_type="application/octet-stream"
                    )
                except Exception:
                    pass

            new_kb = KnowledgeBase(
                name=new_name,
                file_ext=kb.file_ext,
                file_size=kb.file_size,
                minio_key=new_minio_key,
                status=kb.status,
                creator_id=user_id,
                category_id=kb.category_id,
                is_folder=False,
                parent_id=target_parent_id,
                path=f"{target_path}{new_name}",
                level=target_level
            )
            self.db.add(new_kb)
            await self.db.commit()
            await self.db.refresh(new_kb)

        return {"success": True, "data": new_kb}

    async def delete(self, kb_id, user_id: str) -> dict:
        """移入回收站（级联移入子项）"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        # 权限检查：只有创建人可以删除
        if kb.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以删除"}

        now = datetime.now()

        # 如果是文件夹，递归移入回收站
        if kb.is_folder:
            children = await self.get_children(kb_id)
            for child in children:
                await self.delete(child.id, user_id)

        # 移入回收站（保留数据，记录删除时间）
        kb.is_deleted = True
        kb.deleted_at = now
        kb.deleted_by = user_id
        await self.db.commit()
        return {"success": True, "message": "已移入回收站"}

    async def get_recycle_bin(self, user_id: str = None, keyword: str = None,
                              page: int = 1, size: int = 20) -> PageData:
        """获取回收站列表（只显示顶级项，子项通过树形结构展示）"""
        # 查询所有已删除的项
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.is_deleted == True,
            KnowledgeBase.deleted_at.isnot(None)
        )

        # 只看自己删除的
        if user_id:
            stmt = stmt.where(KnowledgeBase.deleted_by == user_id)

        # 搜索
        if keyword:
            like_pattern = f"%{keyword}%"
            stmt = stmt.where(
                KnowledgeBase.name.ilike(like_pattern) |
                KnowledgeBase.title.ilike(like_pattern)
            )

        stmt = stmt.order_by(KnowledgeBase.deleted_at.desc())
        result = await paginate(self.db, stmt, page, size)

        # 过滤：只保留顶级项（父级未删除或父级为"0"）
        filtered_items = []
        for item in result.items:
            # 如果是根目录项，直接保留
            if not item.parent_id or item.parent_id == "0":
                filtered_items.append(item)
            else:
                # 检查父级是否也在回收站
                parent = await self.get_by_id(item.parent_id)
                if not parent or not parent.is_deleted:
                    # 父级未删除，这是顶级被删项
                    filtered_items.append(item)
                # 如果父级也在回收站，不显示（会被父级的树形结构包含）

        result.items = filtered_items
        return result

    async def restore(self, kb_id, user_id: str) -> dict:
        """从回收站恢复"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        if not kb.is_deleted:
            return {"success": False, "message": "该文件不在回收站中"}

        # 只有当父级也在回收站时才需要先恢复父级
        # 如果父级是 "0"（根目录）或父级未删除，则可以直接恢复
        if kb.parent_id and kb.parent_id != "0":
            parent = await self.get_by_id(kb.parent_id)
            if parent and parent.is_deleted:
                # 父级也在回收站，需要先恢复父级
                return {"success": False, "message": "父文件夹也在回收站中，请先恢复父文件夹"}

        # 先恢复当前项（这样子项恢复时就不会报错）
        kb.is_deleted = False
        kb.deleted_at = None
        kb.deleted_by = None
        await self.db.commit()

        # 再恢复子项（递归）
        if kb.is_folder:
            children = await self._get_deleted_children(kb_id)
            for child in children:
                await self.restore(child.id, user_id)

        return {"success": True, "message": "恢复成功"}

    async def _get_deleted_children(self, parent_id) -> list:
        """获取已删除的子项"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.parent_id == parent_id,
            KnowledgeBase.is_deleted == True
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def permanent_delete(self, kb_id, user_id: str) -> dict:
        """彻底删除（删除 MinIO 文件 + 数据库记录）"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        if not kb.is_deleted:
            return {"success": False, "message": "该文件不在回收站中"}

        # 彻底删除子项
        if kb.is_folder:
            children = await self._get_deleted_children(kb_id)
            for child in children:
                await self.permanent_delete(child.id, user_id)

        # 删除 MinIO 文件
        await self.minio_client.init()
        if kb.minio_key:
            try:
                await self.minio_client.remove_object(settings.MINIO_BUCKET, kb.minio_key)
            except Exception:
                pass
        if kb.parsed_minio_key:
            try:
                await self.minio_client.remove_object(settings.MINIO_BUCKET, kb.parsed_minio_key)
            except Exception:
                pass
        if kb.metadata_minio_key:
            try:
                await self.minio_client.remove_object(settings.MINIO_BUCKET, kb.metadata_minio_key)
            except Exception:
                pass

        # 删除数据库记录
        await self.db.delete(kb)
        await self.db.commit()
        return {"success": True, "message": "已彻底删除"}

    async def clear_recycle_bin(self, user_id: str) -> dict:
        """清空回收站（彻底删除所有）"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.is_deleted == True,
            KnowledgeBase.deleted_by == user_id
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        # 只删除顶级项（子项会被级联删除）
        root_items = [item for item in items if item.parent_id == "0" or not self._is_child_of_any(item, items)]

        for item in root_items:
            await self.permanent_delete(item.id, user_id)

        return {"success": True, "message": f"已清空回收站，共删除 {len(root_items)} 个项目"}

    def _is_child_of_any(self, item, items) -> bool:
        """检查是否是其他项的子项"""
        for other in items:
            if other.id != item.id and item.path.startswith(other.path) and other.is_folder:
                return True
        return False

    async def rename(self, kb_id, new_name: str, user_id: str) -> dict:
        """重命名文件/文件夹"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        # 权限检查
        if kb.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以重命名"}

        # 检查重名
        unique_name = await self._get_unique_name(new_name, kb.parent_id, kb.is_folder)

        old_name = kb.name
        kb.name = unique_name

        # 更新 path（替换旧名称为新名称）
        if kb.is_folder:
            kb.path = kb.path.replace(f"{old_name}/", f"{unique_name}/", 1)
            # 级联更新子项的 path
            await self._update_children_path(kb.id, kb.path)
        else:
            kb.path = kb.path.replace(old_name, unique_name, 1)

        # 如果是文件，更新 MinIO 中的文件名
        if not kb.is_folder and kb.minio_key:
            await self.minio_client.init()
            import uuid as uuid_module
            new_file_uuid = str(uuid_module.uuid4())
            # 保留原路径，只替换文件名部分
            old_minio_parts = kb.minio_key.rsplit("/", 1)
            if len(old_minio_parts) == 2:
                new_minio_key = f"{old_minio_parts[0]}/{new_file_uuid}_{unique_name}"
                try:
                    file_data = await self.minio_client.get_object(settings.MINIO_BUCKET, kb.minio_key)
                    await self.minio_client.upload_data(
                        bucket_name=settings.MINIO_BUCKET,
                        object_name=new_minio_key,
                        data=file_data,
                        content_type="application/octet-stream"
                    )
                    await self.minio_client.remove_object(settings.MINIO_BUCKET, kb.minio_key)
                    kb.minio_key = new_minio_key
                except Exception:
                    pass

        await self.db.commit()
        await self.db.refresh(kb)
        return {"success": True, "data": kb}

    async def move(self, kb_id, target_parent_id: str, user_id: str) -> dict:
        """移动到目标文件夹"""
        kb = await self.get_by_id(kb_id)
        if not kb:
            return {"success": False, "message": "知识库不存在"}

        # 权限检查：只有创建人可以移动
        if kb.creator_id != user_id:
            return {"success": False, "message": "只有创建人可以移动"}

        # 处理空值
        if not target_parent_id:
            target_parent_id = "0"

        # 不能移动到自己里面
        if target_parent_id == kb_id:
            return {"success": False, "message": "不能移动到自身"}

        # 不能移动到自己的子文件夹（防止无限递归）
        if kb.is_folder and target_parent_id != "0":
            if await self._is_descendant(kb_id, target_parent_id):
                return {"success": False, "message": "不能移动到自身的子文件夹"}

        # 更新 parent_id
        old_parent_id = kb.parent_id
        kb.parent_id = target_parent_id

        # 重新计算 path 和 level
        if target_parent_id == "0":
            kb.path = f"{kb.name}/" if kb.is_folder else kb.name
            kb.level = 0
        else:
            parent = await self.get_by_id(target_parent_id)
            if not parent:
                return {"success": False, "message": "目标文件夹不存在"}
            kb.path = f"{parent.path}{kb.name}/" if kb.is_folder else f"{parent.path}{kb.name}"
            kb.level = parent.level + 1

        # 级联更新子项的 path
        if kb.is_folder:
            await self._update_children_path(kb.id, kb.path)

        await self.db.commit()
        await self.db.refresh(kb)
        return {"success": True, "data": kb}

    async def _update_children_path(self, parent_id: str, parent_path: str):
        """递归更新子项的 path"""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.parent_id == parent_id,
            KnowledgeBase.is_deleted == False
        )
        result = await self.db.execute(stmt)
        children = result.scalars().all()

        for child in children:
            child.path = f"{parent_path}{child.name}" if child.is_folder else f"{parent_path}{child.name}"
            child.level = child.level  # level 需要重新计算
            if child.is_folder:
                await self._update_children_path(child.id, child.path)
