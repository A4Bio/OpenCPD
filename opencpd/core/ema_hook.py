import warnings
from .hooks import Hook


class EMAHook(Hook):
    r"""Exponential Moving Average Hook.

    Use Exponential Moving Average on all parameters of model in training
    process. All parameters have a ema backup, which update by the formula
    as below. EMAHook takes priority over EvalHook and CheckpointSaverHook!

        .. math::
            Xema\_{t+1} = \text{momentum} \times Xema\_{t} +
                (1 - \text{momentum}) \times X_t

    Args:
        momentum (float): The momentum used for updating ema parameter.
            Defaults to 0.9999.
        warmup (string): Type of warmup used. It can be None(use no warmup),
            'constant', 'linear' or 'exp'. Default to None.
        warmup_iters (int): The number of iterations that warmup lasts, i.e.,
            warmup by iteration. Default to 0.
        warmup_ratio (float): Attr used at the beginning of warmup equals to
            warmup_ratio * momentum.
        evaluate_on_ema (bool): Evaluating EMA model. Defaults to true.
        evaluate_on_nonema (bool): Evaluating non-EMA model. Defaults to false.
        full_params_ema (bool): Whether to register EMA parameters by
            `named_parameters()` or `state_dict()`, which influences performances
            of models with BN variants. defaults to False.
        update_interval (int): Update ema parameter every interval iteration.
            Defaults to 1.
    """

    def __init__(self,
                 momentum=0.9999,
                 warmup=None,
                 warmup_iters=0,
                 warmup_ratio=0.9,
                 evaluate_on_ema=True,
                 evaluate_on_nonema=False,
                 full_params_ema=False,
                 update_interval=1,
                 **kwargs):
        assert isinstance(update_interval, int) and update_interval > 0
        assert momentum > 0 and momentum < 1
        self.momentum = momentum
        self.regular_momentum = momentum
        if warmup is not None:
            if warmup not in ['constant', 'linear', 'exp']:
                raise ValueError(
                    f'"{warmup}" is not a supported type for warming up!')
            assert warmup_iters > 0 and 0 < warmup_ratio <= 1.0
        self.warmup = warmup
        self.warmup_iters = warmup_iters
        self.warmup_ratio = warmup_ratio
        self.update_interval = update_interval

        if not evaluate_on_ema and not evaluate_on_nonema:
            warnings.warn(
                'Automatically set `evaluate_on_nonema=True` since the '
                '`evaluate_on_ema` is disabled. If you want to disable '
                'all validation, please modify the `val_interval` of '
                'the `train_cfg`.', UserWarning)
            evaluate_on_nonema = True
        self.evaluate_on_ema = evaluate_on_ema
        self.evaluate_on_nonema = evaluate_on_nonema
        self.full_params_ema = full_params_ema

    def get_warmup_momentum(self, cur_iters):
        if self.warmup == 'constant':
            warmup_m = self.warmup_ratio * self.momentum
        elif self.warmup == 'linear':
            k = (1 - cur_iters / self.warmup_iters) * (1 - self.warmup_ratio)
            warmup_m = (1 - k) * self.momentum
        elif self.warmup == 'exp':
            k = self.warmup_ratio**(1 - cur_iters / self.warmup_iters)
            warmup_m = k * self.momentum
        return warmup_m

    def before_run(self, runner):
        """To resume model with it's ema parameters more friendly.

        Register ema parameter as ``named_buffer`` to model
        """
        model = runner.method.model
        self.param_ema_buffer = {}
        if self.full_params_ema:
            self.model_parameters = dict(model.state_dict())
        else:
            self.model_parameters = dict(model.named_parameters(recurse=True))
        for name, value in self.model_parameters.items():
            # "." is not allowed in module's buffer name
            buffer_name = f"ema_{name.replace('.', '_')}"
            self.param_ema_buffer[name] = buffer_name
            model.register_buffer(buffer_name, value.data.clone())
        self.model_buffers = dict(model.named_buffers(recurse=True))

    def after_train_iter(self, runner):
        """Update ema parameter every self.interval iterations."""
        if self.every_n_iters(runner, self.update_interval):
            curr_iter = runner._iter
            if self.warmup is None or curr_iter > self.warmup_iters:
                self.regular_momentum = self.momentum
            else:
                self.regular_momentum = self.get_warmup_momentum(curr_iter)
            for name, parameter in self.model_parameters.items():
                buffer_name = self.param_ema_buffer[name]
                buffer_parameter = self.model_buffers[buffer_name]
                buffer_parameter.mul_(self.regular_momentum).add_(
                    parameter.data, alpha=1. - self.regular_momentum)

    def after_train_epoch(self, runner):
        """We load parameter values from ema backup to model before the
        EvalHook."""
        self._swap_ema_parameters()

    def before_train_epoch(self, runner):
        """We recover model's parameter from ema backup after last epoch's
        EvalHook."""
        self._swap_ema_parameters()

    def before_val_epoch(self, runner):
        """We load parameter values from ema model to source model before
        validation.

        Args:
            runner (Runner): The runner of the training process.
        """
        if self.evaluate_on_ema:
            # Swap when evaluate on ema
            print('switch to EMA params')
            self._swap_ema_parameters()

    def after_val_epoch(self, runner):
        """We recover source model's parameter from ema model after validation."""
        if self.evaluate_on_ema:
            # Swap when evaluate on ema
            print('switch back to ori params')
            self._swap_ema_parameters()

    def _swap_ema_parameters(self):
        """Swap the parameter of model with parameter in ema_buffer."""
        for name, value in self.model_parameters.items():
            temp = value.data.clone()
            ema_buffer = self.model_buffers[self.param_ema_buffer[name]]
            value.data.copy_(ema_buffer.data)
            ema_buffer.data.copy_(temp)


class SwitchEMAHook(Hook):
    r"""Exponential Moving Average Hook.
    IP120 v01.10, v02.08

    Use Exponential Moving Average on all parameters of model in training
    process. All parameters have a ema backup, which update by the formula
    as below. EMAHook takes priority over EvalHook and CheckpointSaverHook!

        .. math::
            Xema\_{t+1} = \text{momentum} \times Xema\_{t} +
                (1 - \text{momentum}) \times X_t

    Args:
        momentum (float): The momentum used for updating ema parameter.
            Defaults to 0.9999.
        warmup (string): Type of warmup used. It can be None(use no warmup),
            'constant', 'linear' or 'exp'. Default to None.
        warmup_iters (int): The number of iterations that warmup lasts, i.e.,
            warmup by iteration. Default to 0.
        warmup_ratio (float): Attr used at the beginning of warmup equals to
            warmup_ratio * momentum.
        full_params_ema (bool): Whether to register EMA parameters by
            `named_parameters()` or `state_dict()`, which influences performances
            of models with BN variants. defaults to False.
        update_interval (int): Update ema parameter every interval iteration.
            Defaults to 1.
    """

    def __init__(self,
                 momentum=0.9999,
                 warmup=None,
                 warmup_iters=0,
                 warmup_ratio=0.9,
                 switch_params=False,
                 switch_by_iter=False,
                 switch_start=0,
                 switch_end=None,
                 switch_interval=1,
                 full_params_ema=False,
                 update_interval=1,
                 **kwargs):
        assert isinstance(update_interval, int) and update_interval > 0
        assert momentum > 0 and momentum < 1
        self.momentum = momentum
        self.regular_momentum = momentum
        if warmup is not None:
            if warmup not in ['constant', 'linear', 'exp']:
                raise ValueError(
                    f'"{warmup}" is not a supported type for warming up!')
            assert warmup_iters > 0 and 0 < warmup_ratio <= 1.0
        self.warmup = warmup
        self.warmup_iters = warmup_iters
        self.warmup_ratio = warmup_ratio
        self.update_interval = update_interval

        self.switch_params = switch_params
        self.switch_by_iter = switch_by_iter
        self.switch_start = switch_start
        self.switch_end = switch_end \
            if isinstance(switch_end, int) and self.switch_params else 1e100
        self.switch_interval = switch_interval
        self.full_params_ema = full_params_ema

    def get_warmup_momentum(self, cur_iters):
        if self.warmup == 'constant':
            warmup_m = self.warmup_ratio * self.momentum
        elif self.warmup == 'linear':
            k = (1 - cur_iters / self.warmup_iters) * (1 - self.warmup_ratio)
            warmup_m = (1 - k) * self.momentum
        elif self.warmup == 'exp':
            k = self.warmup_ratio**(1 - cur_iters / self.warmup_iters)
            warmup_m = k * self.momentum
        return warmup_m

    def before_run(self, runner):
        """To resume model with it's ema parameters more friendly.

        Register ema parameter as ``named_buffer`` to model
        """
        model = runner.method.model
        self.param_ema_buffer = {}
        if self.full_params_ema:
            self.model_parameters = dict(model.state_dict())
        else:
            self.model_parameters = dict(model.named_parameters(recurse=True))
        for name, value in self.model_parameters.items():
            # "." is not allowed in module's buffer name
            buffer_name = f"ema_{name.replace('.', '_')}"
            self.param_ema_buffer[name] = buffer_name
            model.register_buffer(buffer_name, value.data.clone())
        self.model_buffers = dict(model.named_buffers(recurse=True))

    def after_train_iter(self, runner):
        """Update ema parameter every self.interval iterations."""
        if self.every_n_iters(runner, self.update_interval):
            curr_iter = runner._iter
            if self.warmup is None or curr_iter > self.warmup_iters:
                self.regular_momentum = self.momentum
            else:
                self.regular_momentum = self.get_warmup_momentum(curr_iter)
            for name, parameter in self.model_parameters.items():
                buffer_name = self.param_ema_buffer[name]
                buffer_parameter = self.model_buffers[buffer_name]
                buffer_parameter.mul_(self.regular_momentum).add_(
                    parameter.data, alpha=1. - self.regular_momentum)
        # copy EMA to the model
        if self.switch_params and self.switch_by_iter:
            if self.switch_start < curr_iter < self.switch_end:
                if not self.every_n_iters(runner, self.switch_interval):
                    self._switch_ema_parameters()

    def after_train_epoch(self, runner):
        """We load parameter values from ema backup to model before the
        EvalHook."""
        if self.switch_end < runner._epoch:
            return
        self._swap_ema_parameters()

    def before_train_epoch(self, runner):
        """We recover model's parameter from ema backup after last epoch's
        EvalHook."""
        if self.switch_end < runner._epoch:
            return
        self._swap_ema_parameters()
        if self.switch_params and not self.switch_by_iter:  # copy EMA to the model
            if self.switch_start < runner._epoch:
                if not self.every_n_epochs(runner, self.switch_interval):
                    self._switch_ema_parameters()

    def before_val_epoch(self, runner):
        """We load parameter values from ema model to source model before
        validation.

        Args:
            runner (Runner): The runner of the training process.
        """
        self._swap_ema_parameters()

    def after_val_epoch(self, runner):
        """We recover source model's parameter from ema model after validation."""
        self._swap_ema_parameters()

    def _swap_ema_parameters(self):
        """Swap the parameter of model with parameter in ema_buffer."""
        for name, value in self.model_parameters.items():
            temp = value.data.clone()
            ema_buffer = self.model_buffers[self.param_ema_buffer[name]]
            value.data.copy_(ema_buffer.data)
            ema_buffer.data.copy_(temp)

    def _switch_ema_parameters(self):
        """Switch the parameter of model to parameters in ema_buffer."""
        for name, value in self.model_parameters.items():
            ema_buffer = self.model_buffers[self.param_ema_buffer[name]]
            value.data.copy_(ema_buffer.data)
