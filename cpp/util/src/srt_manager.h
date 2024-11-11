#ifndef SRT_MANAGER_H_
#define SRT_MANAGER_H_
#include <srt/srt.h>

class SRTManager
{
public:
    SRTManager();
    ~SRTManager();

    // functions
    int create_socket();
    int connect();
    void send_data();



private:
    // variables
    SRTSOCKET socket;
};

#endif // SRT_MANAGER_H_