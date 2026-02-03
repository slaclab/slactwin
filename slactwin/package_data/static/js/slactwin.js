'use strict';
SIREPO.srdbg = console.log.bind(console);

SIREPO.app.config(function() {
    SIREPO.SINGLE_FRAME_ANIMATION = [
        'bunchAnimation1',
        'bunchAnimation2',
        'bunchAnimation3',
    ];
    SIREPO.PLOTTING_SUMMED_LINEOUTS = true;
    SIREPO.lattice = {
        elementColor: {
            // override red (alarm) color
            QUADRUPOLE: 'orange',
            BMAPXY: 'magenta',
            FTABLE: 'magenta',
            KOCT: 'lightyellow',
            KQUAD: 'tomato',
            KSEXT: 'lightgreen',
            MATTER: 'black',
            OCTU: 'yellow',
            QUAD: 'orange',
            QUFRINGE: 'salmon',
            SEXT: 'lightgreen',
            VKICK: 'blue',
            LMIRROR: 'lightblue',
            REFLECT: 'blue',
            // override yellow (warning) color
            LCAVITY: 'lightgreen',
            RFCW: 'lightgreen',
        },
        elementPic: {
            alpha: ['ALPH'],
            aperture: ['APCONTOUR', 'CLEAN', 'ECOL', 'MAXAMP', 'PEPPOT', 'RCOL', 'SCRAPER', 'TAPERAPC', 'TAPERAPE', 'TAPERAPR', 'RCOLLIMATOR'],
            bend: ['BRAT', 'BUMPER', 'CCBEND', 'CSBEND', 'CSRCSBEND', 'FMULT', 'FTABLE', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND', 'SBEND'],
            drift: ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT', 'DRIFT', 'EMFIELD_CARTESIAN', 'EMFIELD_CYLINDRICAL', 'WAKEFIELD', 'PIPE', 'EM_FIELD'],
            lens: ['ROTATIONALLY_SYMMETRIC_TO_3D', 'LTHINLENS'],
            magnet: ['BMAPXY', 'BOFFAXE', 'HKICK', 'KICKER', 'KOCT', 'KQUAD', 'KSEXT', 'MATTER', 'OCTU', 'POLYSERIES', 'QUAD', 'QUFRINGE', 'SEXT', 'VKICK', 'QUADRUPOLE', 'DIPOLE', 'SOL_QUAD'],
            malign: ['MALIGN'],
            mirror: ['LMIRROR'],
            recirc: ['RECIRC'],
            rf: ['CEPL', 'FRFMODE', 'FTRFMODE', 'MODRF', 'MRFDF', 'RAMPP', 'RAMPRF', 'RFCA', 'RFCW', 'RFDF', 'RFMODE', 'RFTM110', 'RFTMEZ0', 'RMDF', 'SHRFDF', 'TMCF', 'TRFMODE', 'TWLA', 'TWMTA', 'TWPL', 'LCAVITY'],
            solenoid: ['MAPSOLENOID', 'SOLE', 'SOLENOID', 'SOLRF'],
            undulator: ['CORGPIPE', 'CWIGGLER', 'GFWIGGLER', 'LSRMDLTR', 'MATR', 'UKICKMAP', 'WIGGLER', 'TAYLOR'],
            watch: ['WATCH', 'WRITE_BEAM', 'MONITOR', 'MARKER'],
            zeroLength: ['BRANCH', 'CENTER', 'CHARGE', 'DSCATTER', 'ELSE', 'EMITTANCE', 'ENERGY', 'FLOOR', 'HISTOGRAM', 'IBSCATTER', 'ILMATRIX', 'IONEFFECTS', 'MAGNIFY', 'MHISTOGRAM', 'PFILTER', 'REFLECT','REMCOR', 'RIMULT', 'ROTATE', 'SAMPLE', 'SCATTER', 'SCMULT', 'SCRIPT', 'SLICE', 'SREFFECTS', 'STRAY', 'TFBDRIVER', 'TFBPICKUP', 'TRCOUNT', 'TRWAKE', 'TWISS', 'WAKE', 'ZLONGIT', 'ZTRANSVERSE', 'CHANGE_TIMESTEP', 'OFFSET_BEAM', 'SPACECHARGE', 'STOP'],
        },
    };
    SIREPO.appFieldEditors += `
        <div data-ng-switch-when="SearchTerms">
          <div data-search-terms="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="ColumnList" data-ng-class="fieldClass">
          <div data-column-list="" data-model="model" data-field="field"></div>
        </div>
        <div data-ng-switch-when="FrameSlider" class="col-sm-12">
          <div data-frame-slider="" data-model="model" data-field="field"></div>
        </div>
    `;
    SIREPO.appReportTypes = `
        <div data-ng-switch-when="parameterWithExternalLattice" data-parameter-with-lattice="" class="sr-plot sr-screenshot" data-model-name="{{ modelKey }}" data-path-to-models="externalLattice"></div>
    `;
});

SIREPO.app.factory('slactwinService', function(activeSection, appState, frameCache, panelState, persistentSimulation, requestSender, uri, $location, $rootScope) {
    const self = {};
    self.computeModel = (analysisModel) => 'animation';
    self.runKinds = null;
    self.selectSearchFieldText = 'Select Search Field';
    self.BUNCH_ANIMATIONS = ['bunchAnimation1', 'bunchAnimation2', 'bunchAnimation3'];

    const isModalVisible = () => $('.sr-modal-shown').length > 0;

    const loadComparisons = () => {
        self.callDB(
            'comparison_summaries',
            {
                run_summary_id: self.getRunSummaryId(),
            },
            (resp) => {
                if (resp.comparisonSummaries && resp.comparisonSummaries.length) {
                    self.comparisonSummaries = resp.comparisonSummaries;
                }
                else {
                    self.comparisonSummaries = null;
                }
            },
        );
    };

    self.callDB = (api_name, api_args, callback) => {
        requestSender.sendStatelessCompute(
            appState,
            (resp) => {
                if (resp.error) {
                    errorService.alertText(resp.error);
                    return;
                }
                callback(resp);
            },
            {
                method: 'db_api',
                args: {
                    api_name,
                    api_args,
                },
                simulationId: SIREPO.nonSimulationId,
            },
        );
    };

    self.elementForName = (name) => {
        for (const el of self.latticeModels().elements) {
            if (el.name === name) {
                return el;
            }
        }
        return null;
    };

    self.formatColumn = (col) => {
        return col.replace(/^.*?\^/, '');
    };

    self.getRunSummaryId = () => {
        return parseInt($location.search().runSummaryId);
    };

    self.hasPVDataFrame = () => {
        return self.summary.pv_mapping_dataframe.el_id;
    };

    self.initDetailController = (controller, $scope) => {
        let firstCheck = true;
        $scope.loadingMessage = 'Reading Run Info';

        const init = () => {
            controller.simScope = $scope;
            controller.simComputeModel = 'animation';
            controller.simState = persistentSimulation.initSimulationState(controller);
        };

        controller.simHandleStatus = (status) => {
            if (self.loadFromStatus($scope, status)) {
                return;
            }
            if (status.frameCount > 0) {
                self.loadRun($scope);
                return;
            }
            if (firstCheck) {
                firstCheck = false;
                if (controller.simState.isStopped()) {
                    controller.simState.runSimulation();
                }
            }
        };

        init();
    };

    self.initMachines = (callback) => {

        const updateFromRunKinds = () => {
            if (appState.isLoaded()) {
                const v = {
                    machine_name: [],
                    twin_name: [],
                };
                for (const r of self.runKinds) {
                    if (! v.machine_name.includes(r.machine_name)) {
                        v.machine_name.push(r.machine_name);
                    }
                    if (r.machine_name === appState.models.simulation.machine_name) {
                        v.twin_name.push(r.twin_name);
                    }
                }
                appState.models.searchSettings.valueList = v;
                appState.saveQuietly('searchSettings');
            }
            if (callback) {
                callback(self.runKinds);
            }
        };

        if (self.runKinds) {
            updateFromRunKinds();
            return;
        }
        requestSender.sendRequest(
            'slactwinListMachines',
            (resp) => {
                if (resp.error) {
                    errorService.alertText(resp.error);
                    return;
                }
                self.runKinds = resp.run_kinds;
                updateFromRunKinds();
            },
            {},
        );
    };

    self.isLiveView = () => {
        return appState.models.searchSettings.isLive == '1';
    };

    self.latticeModels = () => {
        return appState.models.externalLattice.models;
    };

    self.loadFromStatus = ($scope, status) => {
        if (self.isLiveView()
            && status.state === 'running'
            && status.outputInfo
            && status.outputInfo.runSummaryId
        ) {
            if (parseInt(status.outputInfo.runSummaryId) !== self.getRunSummaryId()) {
                const c = activeSection.getActiveSection();
                if (['lattice', 'visualization'].includes(c)) {
                    self.openRun(status.outputInfo.runSummaryId, c);
                    self.loadRun($scope);
                    return true;
                }
                else {
                    self.openRun(status.outputInfo.runSummaryId);
                }
            }
        }
        return false;
    };

    self.loadRun = ($scope) => {
        const runSummaryId = self.getRunSummaryId();
        if ($scope.runSummaryId && isModalVisible()) {
            // don't load a new plot if the modal is visible - the modal would automatically dismiss
            return;
        }
        //TODO(pjm): a modal may be dismissed when
        // it is in a bad state (partially shown) and it doesn't clean up
        // the modal backdrop in that case.
        $('.modal-backdrop').remove();
        if ($scope.runSummaryId === runSummaryId) {
            return;
        }
        $scope.runSummaryId = runSummaryId;
        for (const m in appState.models) {
            if (appState.models[m] && 'runSummaryId' in appState.models[m]) {
                appState.models[m].runSummaryId = runSummaryId;
                appState.saveQuietly(m);
            }
        }
        //TODO(pjm): sr-run-loaded only gets broadcast if summaryAnimation is visible
        if (panelState.isHidden('summaryAnimation')) {
            panelState.toggleHidden('summaryAnimation');
        }
        frameCache.getFrame('summaryAnimation', 0, false, (index, data) => {
            //TODO(pjm): ensure runSummary matches expected, otherwise ignore
            if (data.error) {
                throw new Error(`Failed to load runSummaryId: ${runSummaryId}`);
            }
            frameCache.setFrameCount(1);
            self.summary = data.summary;
            self.particles = data.particles;
            appState.models.externalLattice = data.lattice;
            self.setValueList(appState.models.statAnimation, 'statAnimation', data.stat_columns);
            $rootScope.$broadcast('sr-run-loaded');
            panelState.waitForUI(() => appState.updateReports());
            loadComparisons();
        });
    };

    $rootScope.$on('modelsUnloaded', () => {
        self.summary = null;
        self.particles = null;
        self.comparisonSummaries = null;
    });


    self.openRun = (runSummaryId, route) => {
        uri.localRedirect(route || SIREPO.APP_SCHEMA.appModes.default.localRoute, {
            ':simulationId': appState.models.simulation.simulationId,
        });
        self.setRunSummaryId(runSummaryId);
    };

    self.selectElementId = (id) => {
        self.latticeModels().beamlines[0].items.forEach((v, idx) => {
            if (id === v) {
                $rootScope.$broadcast('sr-beamlineItemSelected', idx);
            }
        });
    };

    self.setRunSummaryId = (runSummaryId) => {
        $location.search('runSummaryId', runSummaryId);
    };

    self.setValueList = (model, modelName, values) => {
        model.valueList = {};
        for (const [f, d] of Object.entries(SIREPO.APP_SCHEMA.model[modelName])) {
            if (d[1] === 'ValueList') {
                model.valueList[f] = values;
            }
        }
    };

    appState.setAppService(self);

    return self;
});

SIREPO.app.factory('liveService', function(appState, persistentSimulation, slactwinService) {
    const self = {};
    const controllerProxy = {
        simComputeModel: 'animation',
    };

    const simStatus = (simScope, callback) => {
        controllerProxy.simScope = simScope;
        simScope.$on('$destroy', () => {
            callback = null;
        });
        controllerProxy.simHandleStatus = (status) => {
            if (callback) {
                callback(controllerProxy.simState, status);
            }
        };
        controllerProxy.simState = persistentSimulation.initSimulationState(controllerProxy);
    };

    self.cancelLiveView = (simScope, callback) => {
        appState.models.searchSettings.isLive = '0';
        appState.saveChanges('searchSettings', () => {
            simStatus(simScope, (simState, status) => {
                if (controllerProxy.simState.isProcessing()) {
                    simState.cancelSimulation();
                }
                callback();
            });
        });
    };

    self.startLiveView = (simScope) => {
        appState.models.searchSettings.isLive = '1';
        appState.saveChanges('searchSettings', () => {
            let firstCheck = true;
            simStatus(simScope, (simState, status) => {
                if (slactwinService.loadFromStatus(simScope, status)) {
                    return;
                }
                if (controllerProxy.simState.isProcessing()) {
                    // already running
                    firstCheck = false;
                }
                if (firstCheck) {
                    firstCheck = false;
                    controllerProxy.simState.runSimulation();
                }
            });
        });
    };

    return self;
});

SIREPO.app.controller('VizController', function(appState, frameCache, liveService, panelState, slactwinService, $scope) {
    const self = this;
    slactwinService.initDetailController(self, $scope);

    self.errorWatch = () => {
        if ($scope.loadingMessage && panelState.getError('summaryAnimation')) {
            panelState.clear('summaryAnimation');
            slactwinService.initDetailController(self, $scope);
        }
    };

    $scope.$on('sr-run-loaded', () => {
        $scope.loadingMessage = '';
        self.outputFiles = [];
        slactwinService.particles.forEach((info) => {
            self.outputFiles.push({
                info: info,
                reportType: 'heatmap',
                viewName: 'elementAnimation',
                modelAccess: {
                    modelKey: info.modelKey,
                    getData: () => {
                        return appState.models[info.modelKey];
                    },
                },
                panelTitle: info.name.replace('_', ' '),
            });
            panelState.setError(info.modelKey, null);
            if (! appState.models[info.modelKey]) {
                appState.models[info.modelKey] = {};
            }
            const m = appState.models[info.modelKey];
            m.runSummaryId = slactwinService.getRunSummaryId();
            m.plotName = info.name;
            slactwinService.setValueList(m, 'elementAnimation', info.columns);
            appState.setModelDefaults(m, 'elementAnimation');
            appState.saveQuietly(info.modelKey);
            frameCache.setFrameCount(1, info.modelKey);
        });
    });
});

SIREPO.app.controller('InitController', function(appState, slactwinService, uri) {
    const self = this;
    const init = () => {
        slactwinService.setRunSummaryId(null);
        appState.clearModels();
        slactwinService.initMachines((result) => {
            uri.localRedirect('search-results', {
                ':simulationId': result[0].simulationId,
            });
        });
    };

    init();
});

SIREPO.app.controller('SearchController', function(appState, liveService, $scope) {
    const self = this;
    self.appState = appState;
    self.canViewLive = false;
    liveService.cancelLiveView($scope, () => self.canViewLive = true);
});

SIREPO.app.controller('BeamController', function() {
    const self = this;
});

SIREPO.app.controller('ComparisonController', function(appState, frameCache, slactwinService, $scope) {
    const self = this;
    slactwinService.initDetailController(self, $scope);
    $scope.slactwinService = slactwinService;
    $scope.$watch('slactwinService.comparisonSummaries', () => {
        const c = slactwinService.comparisonSummaries;
        if (c && c.length) {
            //TODO(pjm): assume only 1 comparison for now
            const s = c[0].run_summary_id;
            for (const m of ['twissAnimation', ...slactwinService.BUNCH_ANIMATIONS]) {
                appState.models[m].comparisonRunSummaryId = s;
            }
            self.comparisonTwinName = c[0].twin_name;
            for (const m of slactwinService.BUNCH_ANIMATIONS) {
                frameCache.setFrameCount(slactwinService.particles.length, m);
            }
        }
    });
    $scope.$on('sr-run-loaded', () => {
        $scope.loadingMessage = '';
        const m = appState.models.bunchAnimation;
        slactwinService.setValueList(m, 'bunchAnimation', slactwinService.particles[0].columns);
        appState.setModelDefaults(m, 'bunchAnimation');
        appState.saveQuietly('bunchAnimation');
    });
});

SIREPO.app.controller('LatticeController', function(liveService, slactwinService, $scope) {
    const self = this;
    slactwinService.initDetailController(self, $scope);
    $scope.slactwinService = slactwinService;

    $scope.$on('sr-run-loaded', () => {
        $scope.loadingMessage = '';
        self.hasLattice = true;
    });
});

SIREPO.app.directive('appFooter', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appFooter',
        },
        template: `
            <div data-common-footer="nav"></div>
            <div data-confirmation-modal=""
                data-id="sr-open-sim"
                data-title="Open as a new {{ sirepoSimTypeName() }} simulation"
                data-cancel-text="{{ newSimURL ? 'Close' : 'Cancel' }}"
                data-ok-text="{{ newSimURL || processingMessage ? '' : 'Create' }}"
                data-ok-clicked="createSim()"
            >
              <div data-ng-if="! newSimURL && ! processingMessage">
                <p>Create a Sirepo {{ sirepoSimTypeName() }} simulation from this run summary?</p>
              </div>
              <div data-ng-if="processingMessage"><p>
                  <span class="glyphicon glyphicon-hourglass"> </span>
                  {{ processingMessage }}
              </p></div>
              <div data-ng-if="newSimURL">
                <p>{{ sirepoSimTypeName() }} simulation created:</p>
                <p><a data-ng-click="closeModal()" href="{{ newSimURL }}" target="_blank">{{ newSimName }} </a></p>
            </div>
        `,
        controller: function(appState, requestSender, slactwinService, uri, $location, $scope) {

            const init = () => {
                $scope.newSimName = '';
                $scope.newSimURL = '';
                $scope.processingMessage = '';
            };

            $scope.closeModal = () => $('#sr-open-sim').modal('hide');

            $scope.createSim = () => {
                $scope.processingMessage = `Creating ${$scope.sirepoSimTypeName()} simulation, please wait.`;

                requestSender.sendRequest(
                    'slactwinSimFromRunSummary',
                    (resp) => {
                        if (resp.error) {
                            $scope.processingMessage = `An error occurred: ${resp.error}`;
                            return;
                        }
                        $scope.processingMessage = "";
                        $scope.newSimName = resp.simulation.name;
                        $scope.newSimURL = uri.formatLocal(
                            'lattice',
                            { simulationId: resp.simulation.simulationId },
                            resp.simulationType,
                        );
                    },
                    {
                        runSummaryId: slactwinService.getRunSummaryId(),
                        runSummaryUrl: $location.absUrl(),
                    },
                );

                $('#sr-open-sim').on('hidden.bs.modal', () => {
                    init();
                    $('#sr-open-sim').off('hidden.bs.modal');
                });

                // stay on the modal when Create is selected
                return false;
            };

            $scope.sirepoSimTypeName = () => {
                if (appState.isLoaded()) {
                    //TODO(pjm): name should be created on server
                    const t = appState.models.simulation.twin_name;
                    if (t === 'impact') {
                        return 'Impact-T';
                    }
                    if (t === 'elegant') {
                        return t;
                    }
                    if (t === 'bmad') {
                        return 'Bmad';
                    }
                    throw new Error(`Unhandled twin_name: ${t}`);
                }
                return '';
            };

            init();
        },
    };
});

SIREPO.app.directive('appHeader', function() {
    return {
        restrict: 'A',
        scope: {
            nav: '=appHeader',
        },
        template: `
            <div data-app-header-brand="nav"></div>
            <ul class="nav navbar-nav" data-ng-if=":: authState.isLoggedIn">
              <li class="sim-section" data-ng-class="{active: nav.isActive('search') || nav.isActive('search-results') }"><a href data-ng-click="openSearch()"><span class="glyphicon glyphicon-search"></span> Search</a></li>
              <li data-ng-if="appState.isLoaded() && ! nav.isActive('search-results')" style="padding: 15px">{{ appState.models.simulation.name }}</li>
            </ul>
            <div data-app-header-right="nav">
              <app-header-right-sim-loaded data-ng-if="hasQuery()">
                <div data-sim-sections="">
                  <li class="sim-section" data-ng-class="{active: nav.isActive('lattice')}"><a href data-ng-click="nav.openSection('lattice')"><span class="glyphicon glyphicon-option-horizontal"></span> Lattice</a></li>
                  <li class="sim-section" data-ng-class="{active: nav.isActive('visualization')}"><a href data-ng-click="nav.openSection('visualization')"><span class="glyphicon glyphicon-picture"></span> Visualization</a></li>
                  <li class="sim-section" data-ng-if="slactwinService.comparisonSummaries" data-ng-class="{active: nav.isActive('comparison')}"><a href data-ng-click="nav.openSection('comparison')">Comparison</a></li>
                </div>
              </app-header-right-sim-loaded>
              <app-settings>
              </app-settings>
              <app-header-right-sim-list>
              </app-header-right-sim-list>
            </div>
        `,
        controller: function(appState, authState, panelState, uri, slactwinService, $element, $location, $scope) {
            $scope.appState = appState;
            $scope.authState = authState;
            $scope.hasQuery = slactwinService.getRunSummaryId;
            $scope.slactwinService = slactwinService;

            $scope.openSearch = () => {
                if (appState.isLoaded()) {
                    slactwinService.setRunSummaryId(null);
                    uri.localRedirect('search-results', {
                        ':simulationId': appState.models.simulation.simulationId,
                    });
                }
            };

            panelState.waitForUI(() => {
                $($element).find('li[data-settings-menu="nav"]').hide();
            });
        },
    };
});

SIREPO.app.directive('latticeFooter', function(appState) {
    return {
        restrict: 'A',
        scope: {
            width: '@',
            modelName: '@',
        },
        template: ``,
        controller: function(panelState, slactwinService, $scope) {

            const detectOverlap = (positions, pos) => {
                for (let p of positions) {
                    if (rectanglesOverlap(pos, p)) {
                        return p;
                    }
                }
            };

            const labelElements = () => {
                $('.sr-lattice-label').remove();
                const parentRect = $('#sr-lattice')[0].getBoundingClientRect();
                const positions = [];
                const visited = {};
                $("[class^='sr-beamline']").each( (_ , element) => {
                    positions.push(element.getBoundingClientRect());
                });
                $('#sr-lattice').find('title').each((v, node) => {
                    const values = $(node).text().split(': ');
                    const isMonitorOrInstrument = values[1].indexOf('WRITE_BEAM') >= 0
                          || values[1].indexOf('WATCH') >= 0
                          || values[1].indexOf('MARKER') >= 0
                          || values[1].indexOf('MONITOR') >= 0;
                    if (! $scope.names[values[0]] && ! isMonitorOrInstrument || visited[values[0]]) {
                        return;
                    }
                    visited[values[0]] = true;
                    const rect = node.parentElement.getBoundingClientRect();
                    let pos = [
                        rect.left - parentRect.left,
                        isMonitorOrInstrument
                            ? rect.top - parentRect.top - 25
                            : rect.bottom - parentRect.top + 10,

                    ];
                    const el = slactwinService.elementForName(values[0]);
                    let div = $('<div/>', {
                        class: 'sr-lattice-label badge' + (el ? (' sr-lattice-label-' + el._id) : ''),
                    })
                        .html(values[0])
                        .css({
                            left: pos[0],
                            top: pos[1],
                            position: 'absolute',
                            cursor: 'pointer',
                            'user-select': 'none',
                        })
                        .on('click', () => {
                            $scope.elementClicked(values[0]);
                            $scope.$applyAsync();
                        })
                        .appendTo($('.sr-lattice-holder'));
                    const maxChecks = 8;
                    let checkCount = 1;
                    let p = detectOverlap(positions, div[0].getBoundingClientRect());
                    let yOffset = 0;
                    const c = 3;
                    while (p) {
                        if (isMonitorOrInstrument) {
                            const d = div[0].getBoundingClientRect().bottom - p.top - 1;
                            if (d > c) {
                                yOffset -= d;
                            }
                            yOffset -= c;
                        }
                        else {
                            const d = p.bottom - div[0].getBoundingClientRect().top + 1;
                            if (d > c) {
                                yOffset += d;
                            }
                            yOffset += c;
                        }
                        div.css({
                            top: pos[1] + yOffset,
                        });
                        p = detectOverlap(positions, div[0].getBoundingClientRect());
                        if (checkCount++ > maxChecks) {
                            break;
                        }
                    }
                    positions.push(div[0].getBoundingClientRect());
                });
            };

            const rectanglesOverlap = (pos1, pos2) => {
                if (pos1.left > pos2.right || pos2.left > pos1.right) {
                    return false;
                }
                if (pos1.top > pos2.bottom || pos2.top > pos1.bottom) {
                    return false;
                }
                return true;
            };

            const setSelectedId = (elId) => {
                if ($scope.selectedId != elId) {
                    if ($scope.selectedId) {
                        const node = $('.sr-lattice-label-' + $scope.selectedId);
                        node.removeClass('sr-selected-badge');
                    }
                    $scope.selectedId = elId;
                    const node = $('.sr-lattice-label-' + $scope.selectedId);
                    node.addClass('sr-selected-badge');
                }
            };

            $scope.elementClicked = (name) => {
                const el = slactwinService.elementForName(name);
                if (el) {
                    slactwinService.selectElementId(el._id);
                }
            };

            $scope.$on('$destroy', () => $('.sr-lattice-label').off());

            $scope.$on('sr-beamlineItemSelected', (e, idx) => {
                setSelectedId(slactwinService.latticeModels().beamlines[0].items[idx]);
            });

            $scope.$on('sr-renderBeamline', () => {
                const ids = {};
                if (! slactwinService.hasPVDataFrame()) {
                    return;
                }
                const df = slactwinService.summary.pv_mapping_dataframe.el_id;
                for (const el_id of Object.values(df)) {
                    if (el_id) {
                        ids[el_id] = true;
                    }
                }
                $scope.names = {};
                for (const el of slactwinService.latticeModels().elements) {
                    if (ids[el._id]) {
                        $scope.names[el.name] = true;
                    }
                }
                panelState.waitForUI(labelElements);
            });
        },
    };
});

SIREPO.app.directive('pvTable', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <table class="table table-hover table-condensed" data-ng-if="rows">
              <thead><tr>
                <th data-ng-repeat="col in columns track by $index">
                  {{ col[0] }}
                </th>
              </tr></thead>
              <tbody>
                <tr style="cursor: pointer" data-ng-click="selectRow(row)"
                  data-ng-class="{active: isActive(row)}"
                  data-ng-repeat="row in rows track by $index">
                  <td data-ng-repeat="col in columns track by $index"
                    data-ng-class="colClass(row, col)">
                    {{ formatCol(row, col) }}
                    <div data-ng-if="col[2]" class="text-left st-units">{{ formatUnits(row, col) }}</div>
                  </td>
                </tr>
              </tbody>
            <table>
        `,
        controller: function(appState, slactwinService, $scope) {
            const cellValue = (col, col_idx, row_idx) => ($scope.dataframe[col[col_idx]] || [])[row_idx];

            const init = () => {
                $scope.columns = slactwinService.summary.summary_columns;
                $scope.dataframe = slactwinService.summary.pv_mapping_dataframe;
                $scope.rows = [];
                const ids = slactwinService.latticeModels().beamlines[0].items;
                Object.keys($scope.dataframe.el_id).forEach((k, idx) => {
                    $scope.rows.push({
                        el_id: $scope.dataframe.el_id[k],
                        index: idx,
                    });
                });
            };

            const isNumber = (row, col) => {
                const v = cellValue(col, 1, row.index);
                return typeof v === "number" || /^(\-|\d)/.test(v);
            };

            $scope.colClass = (row, col) => isNumber(row, col) ? 'text-right' : 'text-left';

            $scope.formatCol = (row, col) => {
                const v = cellValue(col, 1, row.index);
                if (! SIREPO.NUMBER_REGEXP.test(v)) {
                    return v;
                }
                if (! v && ! col[2]) {
                    return '';
                }
                if (Math.abs(v) < 1e-3) {
                    return appState.formatExponential(v);
                }
                return appState.formatFloat(v, 6);
            };

            $scope.formatUnits = (row, col) => {
                if (col[2]) {
                    return `(${cellValue(col, 2, row.index)})`;
                }
            }

            $scope.isActive = (row) => {
                return row.el_id && row.el_id === $scope.selectedId;
            };

            $scope.selectRow = (row) => {
                if (row.el_id) {
                    slactwinService.selectElementId(row.el_id);
                }
            };

            $scope.$on('sr-beamlineItemSelected', (e, idx) => {
                $scope.selectedId = slactwinService.latticeModels().beamlines[0].items[idx];
            });

            init();

            $scope.slactwinService = slactwinService;
            $scope.$on('sr-run-loaded', init);
        },
    };
});

SIREPO.app.directive('runNavigation', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="text-right" style="margin: 0 25px 15px 0" data-ng-if="slactwinService.isLiveView()"><span class="glyphicon glyphicon-play-circle"></span> Live</div>
            <div class="text-right" data-ng-if="runSummaryIds && ! slactwinService.isLiveView()">
              <div style="margin: 0 15px 15px 0">
                <button title="Open Sirepo Simulation" type="button" class="btn btn-default" data-ng-click="openSim()">
                  <span class="glyphicon glyphicon-file"></span> Open Sim</button>
                <button title="Next" type="button" class="btn btn-default" data-ng-click="next(0)" data-ng-disabled="! runSummaryIds[0]">
                  <span title="Previous" class="glyphicon glyphicon-triangle-left"> </span></button>
                <button type="button" class="btn btn-default" data-ng-click="next(1)" data-ng-disabled="! runSummaryIds[1]">
                  <span class="glyphicon glyphicon-triangle-right"> </span></button>
              </div>
            </div>
        `,
        controller: function(appState, slactwinService, $scope) {

            const init = () => {
                $scope.slactwinService = slactwinService;
                $scope.runSummaryIds = null;
                let prev;
                for (const r of appState.models.searchSettings.rowIds || []) {
                    if ($scope.runSummaryIds) {
                        $scope.runSummaryIds[1] = r;
                        break;
                    }
                    if (r === slactwinService.getRunSummaryId()) {
                        $scope.runSummaryIds = [prev, null];
                    }
                    prev = r;
                }
            };

            $scope.next = (direction) => {
                if ($scope.runSummaryIds[direction]) {
                    slactwinService.setRunSummaryId($scope.runSummaryIds[direction]);
                    slactwinService.loadRun($scope);
                    init();
                }
            };

            $scope.openSim = () => {
                $('#sr-open-sim').modal('show');
            };

            init();
        },
    };
});

SIREPO.app.directive('runSummary', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div>{{ summary.description }}</div>
            <div style="margin-bottom: 1em">{{ dateValue(summary.snapshot_end) }}</div>
            <div data-ng-repeat="r in summary.summary_text track by $index">
                {{ r }}
            </div>
            <div style="margin-top: 1em">Run time: {{ summary.run_time_minutes | number:1 }} minutes</div>
        `,
        controller: function(appState, slactwinService, timeService, $scope) {
            const init = () => {
                $scope.summary = slactwinService.summary;
                $scope.models = slactwinService.latticeModels();
                let cts = {};
                for (const el of $scope.models.elements) {
                    if (el.type === 'CHANGE_TIMESTEP') {
                        cts[el._id] = el;
                    }
                }
                $scope.models.beamlines[0].items.some((id, i) => {
                    if (cts[id]) {
                        $scope.timestep = cts[id];
                        $scope.timestep.pos = $scope.models.beamlines[0].positions[i].elemedge;
                        return true;
                    }
                });
            };

            $scope.dateValue = (value) => {
                if (value) {
                    return timeService.unixTimeToDateString(value);
                }
                return '';
            };

            init();
            $scope.$on('sr-run-loaded', init);
        },
    };
});

SIREPO.app.directive('searchForm', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=searchForm',
        },
        template: `
            <div class="col-md-8 col-md-offset-1">
              <div data-advanced-editor-pane="" data-view-name="'searchSettings'" data-field-def="basic" data-want-buttons="true"></div>
            </div>
            <div class="col-sm-12">
              <div data-search-results-table="searchResults" data-model="model"></div>
              <div data-ng-if="loadingMessage" data-loading-indicator="loadingMessage"></div>
              <div data-ng-if="noResultsMessage">{{ noResultsMessage }}</div>
            </div>
        `,
        controller: function(appState, errorService, liveService, slactwinService, $scope) {
            const init = () => {
                $scope.loadingMessage = 'Loading runs';
                slactwinService.initMachines(() => {
                    slactwinService.callDB(
                        'run_values',
                        {
                            machine_name: appState.models.searchSettings.machine_name,
                            twin_name: appState.models.searchSettings.twin_name,
                        },
                        (resp) => {
                            $scope.loadingMessage = '';
                            slactwinService.runValues = resp.run_values;
                            getSearchResults();
                        },
                    );
                });
            };

            const getSearchFilter = () => {
                $scope.loadingMessage = 'Loading runs';
                const res = {
                    snapshot_end: {},
                };
                if ($scope.model.searchStartTime) {
                    res.snapshot_end.min = $scope.model.searchStartTime;
                }
                if ($scope.model.searchStopTime) {
                    res.snapshot_end.max = $scope.model.searchStopTime;
                }
                for (const m of $scope.model.searchTerms) {
                    if (m.column === slactwinService.selectSearchFieldText
                        || (m.minValue === '' && m.maxValue === '')) {
                        continue;
                    }
                    res[m.column] = {};
                    for (const c of ['min', 'max']) {
                        const v = m[`${c}Value`];
                        if (v !== '') {
                            res[m.column][c] = v;
                        }
                    }
                }
                return res;
            };

            const getSearchResults = () => {
                $scope.noResultsMessage = '';
                $scope.searchResults = null;
                const cols = appState.clone($scope.model.selectedColumns);
                if (! cols) {
                    return;
                }
                // remove snapshot_end col
                cols.shift();
                slactwinService.callDB(
                    'runs_by_date_and_values',
                    {
                        machine_name: $scope.model.machine_name,
                        twin_name: $scope.model.twin_name,
                        min_max_values: getSearchFilter(),
                        additional_run_values: cols,
                    },
                    (resp) => {
                        $scope.loadingMessage = '';
                        $scope.searchResults = resp.rows;
                        $scope.noResultsMessage = resp.rows && resp.rows.length
                            ? ''
                            : 'No records found for the search criteria';
                    });
            };

            init();

            $scope.$on('searchSettings.changed', getSearchResults);
        },
    };
});

SIREPO.app.directive('searchTerms', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <div data-ng-if="showTerms()" class="st-search-terms col-sm-12">
              <div class="row">
                <div class="text-center col-sm-3 col-sm-offset-5"><label>Minimum</label></div>
                <div class="text-center col-sm-3"><label>Maximum</label></div>
              </div>
              <div class="form-group"
                data-ng-repeat="searchTerm in model.searchTerms track by $index"
                data-ng-show="showRow($index)">
                <div class="col-sm-2"></div>
                <div data-field-editor="'column'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div data-field-editor="'minValue'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div data-field-editor="'maxValue'" data-label-size="0"
                   data-field-size="3" data-model-name="'searchTerm'"
                   data-model="searchTerm"></div>
                 <div class="col-sm-1" style="margin-top: 5px; margin-left: -15px"
                   data-ng-show="! isEmpty($index)">
                   <button class="btn btn-info btn-xs" type="button"
                     data-ng-click="deleteRow($index)">
                     <span class="glyphicon glyphicon-remove"></span>
                   </button>
                 </div>
               </div>
            </div>`,
        controller: function(appState, slactwinService, $scope) {
            const maxSearchTerms = 10;
            let isInitialized = false;

            const updateTerms = () => {
                for (let i = 0; i < maxSearchTerms; i++) {
                    if (! $scope.model.searchTerms[i]) {
                        $scope.model.searchTerms[i] = {
                            column: slactwinService.selectSearchFieldText,
                            minValue: '',
                            maxValue: '',
                        };
                    }
                }
            };

            $scope.deleteRow = (idx) => {
                $scope.model.searchTerms.splice(idx, 1);
                updateTerms();
            };

            $scope.isEmpty = (idx) => {
                const search = $scope.model.searchTerms[idx];
                return (
                    search.column != slactwinService.selectSearchFieldText
                    || search.term
                ) ? false : true;
            };

            $scope.showRow = (idx) => (idx == 0) || ! $scope.isEmpty(idx - 1);

            $scope.showTerms = () => {
                if (! slactwinService.runValues) {
                    return false;
                }
                if (! isInitialized) {
                    isInitialized = true;
                    updateTerms();
                }
                return true;
            };
        },
    };
});

SIREPO.app.directive('columnList', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
            field: '=',
        },
        template: `
            <select data-ng-if="columns"
              class="form-control pull-right" style="width: auto"
              data-ng-model="model[field]"
              data-ng-options="col as slactwinService.formatColumn(col) for col in columns">
            </select>
        `,
        controller: function(appState, slactwinService, $scope) {
            $scope.slactwinService = slactwinService;
            const updateColumns = () => {
                $scope.columns = appState.clone(slactwinService.runValues);
                if ($scope.columns) {
                    $scope.columns.unshift(slactwinService.selectSearchFieldText);
                }
            };
            updateColumns();
            $scope.$watch('slactwinService.runValues', updateColumns);
        },
    };
});

SIREPO.app.directive('columnPicker', function() {
    return {
        restrict: 'A',
        scope: {
            model: '=',
        },
        template: `
            <div class="form-group form-group-sm pull-right" style="margin: 0; font-weight: 700">
              <select class="form-control" data-ng-model="selected" ng-change="selectColumn()"
                data-ng-options="col as slactwinService.formatColumn(col) for col in availableColumns">
              </select>
            </div>
        `,
        controller: function(appState, slactwinService, $scope) {
            $scope.slactwinService = slactwinService;
            $scope.selected = null;
            const addColumnText = 'Add Column';

            const setAvailableColumns = () => {
                const v = slactwinService.runValues;
                if (! v) {
                    return;
                }
                $scope.availableColumns = v.filter((value) => ! $scope.model.selectedColumns.includes(value));
                $scope.availableColumns.unshift(addColumnText);
                $scope.selected = addColumnText;
            };

            $scope.selectColumn = () => {
                if ($scope.selected === null) {
                    return;
                }
                $scope.model.selectedColumns.push($scope.selected);
                appState.saveChanges('searchSettings');
            };

            $scope.$watch('slactwinService.runValues', setAvailableColumns);
            $scope.$watchCollection('model.selectedColumns', setAvailableColumns);
        },
    };
});

SIREPO.app.directive('searchResultsTable', function() {
    return {
        restrict: 'A',
        scope: {
            searchResults: '<searchResultsTable',
            model: '=',
        },
        template: `
            <div>
              <div>
                <div data-column-picker="" data-model="model"></div>
                <table class="table">
                  <thead>
                    <tr>
                      <th data-ng-repeat="column in columnHeaders track by $index" class="st-removable-column" style="width: 100px; height: 40px; white-space: nowrap; line-height: 24px">
                        <span style="display: inline-block; min-width: 14px" data-ng-class="arrowClass(column)"></span>
                        <!-- <span style="cursor: pointer" data-ng-click="sortCol(column)">{{ slactwinService.formatColumn(column) }}</span> -->
                        <span>{{ slactwinService.formatColumn(column) }}</span>
                        <button type="submit" class="btn btn-info btn-xs st-remove-column-button" data-ng-if="showDeleteButton($index)" data-ng-click="deleteCol(column)"><span class="glyphicon glyphicon-remove"></span></button>
                      </th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr ng-repeat="row in searchResults track by $index">
                      <td>{{ dateValue(row.snapshot_end) }}</td>
                      <td data-ng-repeat="c in columnHeaders.slice(1)"><div class="text-right">{{ columnValue(row, c) | number:7 }}</div></td>
                      <td style="text-align: right"><div class="sr-button-bar-parent"><div class="sr-button-bar" data-ng-style="{right: positionHoverButton()}"><button class="btn btn-info btn-xs sr-hover-button" data-ng-click="openRun(row)">Open Run</button></div><div></td>
                    </tr>
                </table>
              </div>
            </div>
        `,
        controller: function(appState, panelState, slactwinService, timeService, $scope) {
            $scope.slactwinService = slactwinService;

            const callDigest = () => {
                // evaluate page when the scrollend event occurs, repositions the hover button
                $scope.$applyAsync();
            };

            const updateColumns = () => {
                if (! $scope.model.selectedColumns) {
                    $scope.model.selectedColumns = ['snapshot_end'];
                }
                $scope.columnHeaders = [];
                for (const c of $scope.model.selectedColumns) {
                    $scope.columnHeaders.push(c);
                }
            };

            $scope.arrowClass = (column) => {
                if ($scope.model.sortColumn && (column == $scope.model.sortColumn[0])) {
                    const dir = $scope.model.sortColumn[1] ? 'up' : 'down';
                    return {
                        glyphicon: true,
                        [`glyphicon-arrow-${dir}`]: true,
                    };
                }
                return {};
            };

            $scope.columnValue = (row, column) => {
                return row.run_values[column];
            };

            $scope.dateValue = (value) => {
                return timeService.unixTimeToDateString(value);
            };

            $scope.deleteCol = (column) => {
                $scope.model.selectedColumns.splice(
                    $scope.model.selectedColumns.indexOf(column),
                    1
                );
                appState.saveChanges('searchSettings');
            };

            $scope.openRun = (row) => {
                $scope.model.rowIds = $scope.searchResults.map((r) => r.run_summary_id);
                appState.saveChanges('searchSettings', () => {
                    slactwinService.openRun(row.run_summary_id);
                });
            };

            $scope.positionHoverButton = () => {
                // ensure the hover button is always visible in the viewport
                return (document.body.scrollWidth - window.innerWidth - window.scrollX + 15) + 'px';
            };

            $scope.showDeleteButton = (index) => {
                return index > 0;
            };

            // $scope.sortCol = (column) => {
            //     if ($scope.model.sortColumn && $scope.model.sortColumn[0] == column) {
            //         $scope.model.sortColumn[1] = ! $scope.model.sortColumn[1];
            //     }
            //     else {
            //         $scope.model.sortColumn = [column, false];
            //     }
            // };

            $scope.$watchCollection('model.selectedColumns', updateColumns);

            $scope.$on('$destroy', () => document.removeEventListener('scrollend', callDigest));

            document.addEventListener('scrollend', callDigest);
        },
    };
});

SIREPO.app.directive('viewLiveButton', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="btn btn-default" data-ng-click="openLiveView()"><span
              class="glyphicon glyphicon-play-circle"></span> View Live</div>
            <div data-confirmation-modal="" data-is-required="true" data-id="st-starting-live-modal"
              data-title="Live Monitor" data-ok-text="" data-cancel-text="">
              <p>Please wait, initializing the live monitor.</p>
            </div>
        `,
        controller: function(liveService, $scope) {

            $scope.openLiveView = () => {
                $('#st-starting-live-modal').modal('show');
                liveService.startLiveView($scope);
            };

            $scope.$on('$destroy', () => $('#st-starting-live-modal').modal('hide'));
        },
    };
});

//TODO(pjm): derived from the Sirepo canvas app phaseSpacePlots
SIREPO.app.directive('phaseSpacePlots', function() {
    return {
        restrict: 'A',
        scope: {},
        template: `
            <div class="col-sm-12">
              <div data-simple-panel="bunchAnimation" data-is-report="1">
                <div class="col-sm-6">
                  <div data-field-editor="'selectedFrame'" data-model-name="'bunchAnimation'"
                    data-model="appState.models.bunchAnimation"></div>
                </div>
                <div class="col-sm-6">
                  <div class="pull-right">
                    <div data-ng-repeat="(b, v) in views track by $index"
                      style="display: inline-block; margin-right: 1ex">
                      <button type="button" class="btn btn-default" data-ng-class="{ 'btn-primary': isSelected(v) }"
                        data-ng-click="selectView(v)">{{ b }}</button>
                    </div>
                  </div>
                </div>
                <div class="clearfix"></div>
                <div class="row sr-screenshot">
                  <div class="col-md-4" data-ng-repeat="r in reports track by $index">
                    <div data-ng-if="isHeatmap(r)" data-heatmap="" data-model-name="{{ r }}"></div>
                    <div data-ng-if="! isHeatmap(r)" data-plot3d="" data-model-name="{{ r }}"></div>
                  </div>
                </div>
              </div>
            </div>
        `,
        controller: function(appState, slactwinService, $scope) {
            $scope.appState = appState;
            $scope.views = {
                Horizontal: 'x-px',
                Vertical: 'y-py',
                'Cross-section': 'x-y',
                Energy: 'delta_t-energy',
            };
            $scope.reports = slactwinService.BUNCH_ANIMATIONS;

            $scope.isHeatmap = (report) => {
                return appState.models[report].plotType == 'heatmap';
            };

            $scope.isSelected = (xy) => {
                const b = appState.models.bunchAnimation;
                return [b.x, b.y].join('-') === xy;
            };

            $scope.selectView = (xy) => {
                const [x, y] = xy.split('-');
                const b = appState.models.bunchAnimation;
                b.x = x;
                b.y = y;
                appState.saveChanges('bunchAnimation');
            };

            $scope.$on('bunchAnimation.changed', (e) => {
                const b = appState.models.bunchAnimation;
                const updated = {};
                for (const r of $scope.reports) {
                    const m = appState.models[r];
                    for (const f of ['x', 'y', 'histogramBins', 'colorMap', 'plotType']) {
                        if (b[f] !== m[f]) {
                            m[f] = b[f];
                            updated[r] = true;
                        }
                    }
                }
                appState.saveChanges(Object.keys(updated));
            });
        },
    };
});

//TODO(pjm): derived from the Sirepo canvas app frameSlider
SIREPO.app.directive('frameSlider', function(appState, slactwinService, frameCache, utilities) {
    return {
        restrict: 'A',
        scope: {
            field: '<',
            model: '=',
        },
        template: `
          <div data-ng-if="steps">
            <div data-slider="" data-model="model" data-field="field" data-min="min" data-max="max" data-steps="steps"></div>
          </div>
        `,
        controller: function($scope) {
            function setFrame() {
                const v = $scope.model[$scope.field];
                for (const m of slactwinService.BUNCH_ANIMATIONS) {
                    frameCache.setCurrentFrame(m, v);
                    appState.models[m].frameIndex = v;
                }
                appState.saveChanges(slactwinService.BUNCH_ANIMATIONS);
            }

            function updateRange() {
                if (frameCache.getFrameCount(slactwinService.BUNCH_ANIMATIONS[0])) {
                    const c = frameCache.getFrameCount(slactwinService.BUNCH_ANIMATIONS[0]);
                    $scope.model[$scope.field] = c - 1;
                    $scope.min = 0;
                    $scope.max = c - 1;
                    $scope.steps = c;
                }
                else {
                    $scope.steps = 0;
                }
            }

            $scope.$watch('model[field]', utilities.debounce(setFrame));
            $scope.$on('framesLoaded', updateRange);

            updateRange();
        },
    };
});

SIREPO.viewLogic('searchSettingsView', function(appState, slactwinService, uri, $scope) {

    const redirect = (runKind) => {
        appState.clearModels();
        uri.localRedirect('search-results', {
            ':simulationId': runKind.simulationId,
        });
    };

    const simRedirect = (changedField, otherField) => {
        const ss = appState.models.searchSettings;
        let m = null;
        for (const r of slactwinService.runKinds.reverse()) {
            if (r[changedField] === ss[changedField] ) {
                if (r[otherField] == ss[otherField]) {
                    // exact match, redirect now
                    redirect(r);
                    return;
                }
                if (! m) {
                    // save first partial match
                    m = r;
                }
            }
        }
        if (m) {
            // use first partial match
            redirect(m);
        }
    };

    // not using $scope.watchFields because that includes a debouncer and the
    // switch to the new machine_name should be immediate
    appState.watchModelFields(
        $scope, ['searchSettings.machine_name'],  () => simRedirect('machine_name', 'twin_name'));
    appState.watchModelFields(
        $scope, ['searchSettings.twin_name'],  () => simRedirect('twin_name', 'machine_name'));

});
