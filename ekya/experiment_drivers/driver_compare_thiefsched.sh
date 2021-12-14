#!/bin/bash
# Runs one city at a time through ekya. Good as a sanity check to ensure retraining results in accuracy gains.
set -e

DATASET_PATH='/ekya/datasets/cityscapes/'
MODEL_PATH='/ekya/models/'
HYPS_PATH='utilitysim_schedules/3city_0713_sysprof_fixedseed/hyp_map.json'
INFERENCE_PROFILE_PATH='real_inference_profiles.csv'
#UTILITYSIM_SCHEDULE_KEY='100_1_thief_True'
RETRAINING_PERIOD=200
NUM_TASKS=10
INFERENCE_CHUNKS=10
NUM_GPUS=1
EPOCHS=10  # Matters for fair scheduler
START_TASK=1
TERMINATION_TASK=9
MAX_INFERENCE_RESOURCES=0.25
CITIES=zurich,jena #,cologne
DEFAULT_PARAM_ID=5
MP_RES_PER_TRIAL=0.5
DATASET_NAME=cityscapes

# Run thief scheduler
#for CITIES in jena,zurich,darmstadt jena,zurich jena; do #jena,zurich,darmstadt,stuttgart,tubingen; do
#  SCHEDULER=fair
#  for INFERENCE_WEIGHT in 1 0.25 0.5 0.75; do
#    NUM_CITIES=$(echo "${CITIES}" | awk -F "," ' { print NF } ')
#    echo Running fair scheduler on cities ${CITIES} with weight ${INFERENCE_WEIGHT}
#    python driver_multicity.py --scheduler ${SCHEDULER} \
#             --fair-inference-weight ${INFERENCE_WEIGHT} \
#             --cities ${CITIES} \
#             --log-dir /tmp/ekya_expts/multicity/${NUM_CITIES}cities/${SCHEDULER}_${INFERENCE_WEIGHT} \
#             --retraining-period ${RETRAINING_PERIOD} \
#             --num-tasks ${NUM_TASKS} \
#             --inference-chunks ${INFERENCE_CHUNKS} \
#             --num-gpus ${NUM_GPUS} \
#             --dataset-name ${DATASET_NAME} \
#             --root ${DATASET_PATH} \
#             --use-data-cache \
#             --restore-path ${MODEL_PATH} \
#             --lists-pretrained frankfurt,munster \
#             --hyperparameter-id ${DEFAULT_PARAM_ID} \
#             --start-task ${START_TASK} \
#             --termination-task ${TERMINATION_TASK} \
#             --epochs ${EPOCHS} \
#             --hyps-path ${HYPS_PATH} \
#             --inference-profile-path ${INFERENCE_PROFILE_PATH} \
#             --max-inference-resources ${MAX_INFERENCE_RESOURCES} \
#             --microprofile-resources-per-trial ${MP_RES_PER_TRIAL}
#  done
#done

for CITIES in jena,zurich,darmstadt jena,zurich jena; do #jena,zurich,darmstadt,stuttgart,tubingen; do
  SCHEDULER=thief
  NUM_CITIES=$(echo "${CITIES}" | awk -F "," ' { print NF } ')
  echo Running scheduler ${SCHEDULER} on cities ${CITIES}
  python driver_multicity.py --scheduler ${SCHEDULER} \
           --cities ${CITIES} \
           --log-dir /tmp/ekya_expts/multicity/${NUM_CITIES}cities/${SCHEDULER} \
           --retraining-period ${RETRAINING_PERIOD} \
           --num-tasks ${NUM_TASKS} \
           --inference-chunks ${INFERENCE_CHUNKS} \
           --num-gpus ${NUM_GPUS} \
           --dataset-name ${DATASET_NAME} \
           --root ${DATASET_PATH} \
           --use-data-cache \
           --restore-path ${MODEL_PATH} \
           --lists-pretrained frankfurt,munster \
           --hyperparameter-id ${DEFAULT_PARAM_ID} \
           --start-task ${START_TASK} \
           --termination-task ${TERMINATION_TASK} \
           --epochs ${EPOCHS} \
           --hyps-path ${HYPS_PATH} \
           --inference-profile-path ${INFERENCE_PROFILE_PATH} \
           --max-inference-resources ${MAX_INFERENCE_RESOURCES} \
           --microprofile-resources-per-trial ${MP_RES_PER_TRIAL}
done