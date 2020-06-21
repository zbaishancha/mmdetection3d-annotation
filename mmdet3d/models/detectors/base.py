import os.path as osp

from mmdet3d.core import Box3DMode, show_result
from mmdet.models.detectors import BaseDetector


class Base3DDetector(BaseDetector):
    """Base class for detectors"""

    def forward_test(self, points, img_metas, img=None, **kwargs):
        """
        Args:
            points (list[torch.Tensor]): the outer list indicates test-time
                augmentations and inner torch.Tensor should have a shape NxC,
                which contains all points in the batch.
            img_metas (list[list[dict]]): the outer list indicates test-time
                augs (multiscale, flip, etc.) and the inner list indicates
                images in a batch
            img (list[torch.Tensor], optional): the outer
                list indicates test-time augmentations and inner
                torch.Tensor should have a shape NxCxHxW, which contains
                all images in the batch. Defaults to None.
        """
        for var, name in [(points, 'points'), (img_metas, 'img_metas')]:
            if not isinstance(var, list):
                raise TypeError('{} must be a list, but got {}'.format(
                    name, type(var)))

        num_augs = len(points)
        if num_augs != len(img_metas):
            raise ValueError(
                'num of augmentations ({}) != num of image meta ({})'.format(
                    len(points), len(img_metas)))
        # TODO: remove the restriction of imgs_per_gpu == 1 when prepared
        samples_per_gpu = len(points[0])
        assert samples_per_gpu == 1

        if num_augs == 1:
            img = [img] if img is None else img
            return self.simple_test(points[0], img_metas[0], img[0], **kwargs)
        else:
            return self.aug_test(points, img_metas, img, **kwargs)

    def forward(self, return_loss=True, **kwargs):
        """
        Calls either forward_train or forward_test depending on whether
        return_loss=True. Note this setting will change the expected inputs.
        When `return_loss=True`, img and img_metas are single-nested (i.e.
        torch.Tensor and list[dict]), and when `resturn_loss=False`, img and
        img_metas should be double nested
        (i.e.  list[torch.Tensor], list[list[dict]]), with the outer list
        indicating test time augmentations.
        """
        if return_loss:
            return self.forward_train(**kwargs)
        else:
            return self.forward_test(**kwargs)

    def show_results(self, data, result, out_dir):
        points = data['points'][0]._data[0][0].numpy()
        pts_filename = data['img_metas'][0]._data[0][0]['pts_filename']
        file_name = osp.split(pts_filename)[-1].split('.')[0]

        assert out_dir is not None, 'Expect out_dir, got none.'

        pred_bboxes = result['pts_bbox']['boxes_3d'].tensor.numpy()
        # for now we convert points into depth mode
        if data['img_metas'][0]._data[0][0]['box_mode_3d'] != Box3DMode.DEPTH:
            points = points[..., [1, 0, 2]]
            points[..., 0] *= -1
            pred_bboxes = Box3DMode.convert(
                pred_bboxes, data['img_metas'][0]._data[0][0]['box_mode_3d'],
                Box3DMode.DEPTH)
            pred_bboxes[..., 2] += pred_bboxes[..., 5] / 2
        else:
            pred_bboxes[..., 2] += pred_bboxes[..., 5] / 2
        show_result(points, None, pred_bboxes, out_dir, file_name)
